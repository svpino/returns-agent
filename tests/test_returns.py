import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import after
import before
from common import Store


class ReturnRulesTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.order = self.store.orders['ORD-1001']

    def test_deadline_is_inclusive(self):
        self.order['return_deadline'] = date.today().isoformat()
        self.assertTrue(self.store.lookup_order('ORD-1001')['refund_eligible'])
        self.assertEqual(self.store.refund_order('ORD-1001')['status'], 'refunded')

    def test_backend_rechecks_deadline_after_lookup(self):
        self.assertTrue(self.store.lookup_order('ORD-1001')['refund_eligible'])
        self.order['return_deadline'] = (date.today() - timedelta(days=1)).isoformat()
        self.assertFalse(self.store.lookup_order('ORD-1001')['refund_eligible'])
        self.assertIn('error', self.store.refund_order('ORD-1001'))
        self.assertFalse(self.store.payments)

    def test_receipt_does_not_imply_approval(self):
        self.order['return_approved'] = False
        result = self.store.lookup_order('ORD-1001')
        self.assertEqual(result['order_id'], 'ORD-1001')
        self.assertTrue(result['warehouse_received'])
        self.assertFalse(result['return_approved'])
        self.assertFalse(result['refund_eligible'])
        self.assertIn('error', self.store.refund_order('ORD-1001'))

    def test_receipt_is_independent_of_eligibility(self):
        self.order['warehouse_received'] = False
        result = self.store.lookup_order('ORD-1001')
        self.assertFalse(result['warehouse_received'])
        self.assertTrue(result['return_approved'])
        self.assertTrue(result['refund_eligible'])

    def test_ownership_and_duplicate_protection(self):
        for order_id in ['ORD-2002', 'ORD-9999']:
            self.assertIn('error', self.store.lookup_order(order_id))
            self.assertIn('error', self.store.refund_order(order_id))
        self.assertEqual(self.store.refund_order('ORD-1001')['status'], 'refunded')
        self.assertEqual(self.store.refund_order('ORD-1001')['status'], 'already_refunded')
        self.assertEqual(self.store.payments, {
            'ORD-1001': {'amount_cents': 8000, 'destination': 'original_card'},
        })

    def test_tools_and_bound_refund_target(self):
        self.assertEqual(before.build_agent(self.store).name, 'return_agent')
        self.assertEqual([t.__name__ for t in after.build_checker(self.store).tools], ['lookup_order'])
        request = after.ReturnRequest(order_id='ORD-1001', action='refund')
        tool, = after.build_processor(self.store, request).tools
        self.assertEqual(tool.__name__, 'refund_order')
        with self.assertRaises(TypeError):
            tool('ORD-2002')
        self.assertEqual(tool()['order_id'], 'ORD-1001')


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_request_prints_receipt_and_skips_processor(self):
        request = after.ReturnRequest(order_id='ORD-1001', action='lookup')
        status = after.OrderStatus(return_approved=True, warehouse_received=True, refund_eligible=True)
        with patch.object(after, 'structured', new=AsyncMock(side_effect=[request, status])), \
             patch.object(after, 'run', new=AsyncMock()) as run, \
             patch('builtins.print') as output:
            await after.workflow(Store(), 'Check receipt. Do not refund.')
        run.assert_not_awaited()
        self.assertIn('"warehouse_received":true', output.call_args_list[0].args[1])

    async def test_routing_requires_request_approval_and_eligibility(self):
        for action, approved, eligible, expected in [
            ('lookup', True, True, False),
            ('refund', True, False, False),
            ('refund', False, True, False),
            ('refund', True, True, True),
        ]:
            with self.subTest(action=action, approved=approved, eligible=eligible):
                request = after.ReturnRequest(order_id='ORD-1001', action=action)
                status = after.OrderStatus(return_approved=approved, warehouse_received=True,
                                           refund_eligible=eligible)
                with patch.object(after, 'structured', new=AsyncMock(side_effect=[request, status])), \
                     patch.object(after, 'run', new=AsyncMock()) as run, patch('builtins.print'):
                    await after.workflow(Store(), 'Customer request')
                self.assertEqual(run.await_count, int(expected))
                if expected:
                    self.assertEqual(run.call_args.args[1], request.model_dump_json())


if __name__ == '__main__':
    unittest.main()
