import unittest
from unittest.mock import Mock

from PySide6.QtCore import QThread

from services.data_worker import PortfolioRefreshWorker


class PortfolioRefreshWorkerTestCase(unittest.TestCase):
    @staticmethod
    def collect_emissions(worker):
        emissions = []
        worker.result_ready.connect(
            lambda success, result: emissions.append(
                (success, result)
            )
        )
        return emissions

    def test_worker_is_qthread_and_stores_manager(self):
        data_manager = Mock()

        worker = PortfolioRefreshWorker(
            data_manager
        )

        self.assertIsInstance(worker, QThread)
        self.assertIs(
            worker.data_manager,
            data_manager,
        )

    def test_successful_refresh_is_emitted_unchanged(
        self,
    ):
        result = {
            "total_usdt": 1250.5,
            "assets": [
                {
                    "coin": "BTC",
                }
            ],
        }
        data_manager = Mock()
        data_manager.refresh_portfolio.return_value = (
            True,
            result,
        )
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        return_value = worker.run()

        self.assertIsNone(return_value)
        self.assertEqual(len(emissions), 1)
        self.assertTrue(emissions[0][0])
        self.assertIs(emissions[0][1], result)
        data_manager.refresh_portfolio.assert_called_once_with()

    def test_failed_refresh_result_is_emitted_unchanged(
        self,
    ):
        data_manager = Mock()
        data_manager.refresh_portfolio.return_value = (
            False,
            "API bağlantı hatası",
        )
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        worker.run()

        self.assertEqual(
            emissions,
            [
                (
                    False,
                    "API bağlantı hatası",
                )
            ],
        )

    def test_exception_is_converted_to_error_result(self):
        data_manager = Mock()
        data_manager.refresh_portfolio.side_effect = (
            RuntimeError("refresh failed")
        )
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        worker.run()

        self.assertEqual(
            emissions,
            [
                (
                    False,
                    "refresh failed",
                )
            ],
        )
        data_manager.refresh_portfolio.assert_called_once_with()

    def test_arbitrary_result_object_keeps_identity(self):
        result = object()
        data_manager = Mock()
        data_manager.refresh_portfolio.return_value = (
            True,
            result,
        )
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        worker.run()

        self.assertEqual(len(emissions), 1)
        self.assertIs(emissions[0][1], result)

    def test_signal_emits_boolean_success_value(self):
        data_manager = Mock()
        data_manager.refresh_portfolio.side_effect = [
            (
                True,
                {
                    "value": 1,
                },
            ),
            (
                False,
                {
                    "value": 2,
                },
            ),
        ]
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        worker.run()
        worker.run()

        self.assertEqual(
            emissions,
            [
                (
                    True,
                    {
                        "value": 1,
                    },
                ),
                (
                    False,
                    {
                        "value": 2,
                    },
                ),
            ],
        )
        self.assertIsInstance(
            emissions[0][0],
            bool,
        )
        self.assertIsInstance(
            emissions[1][0],
            bool,
        )

    def test_each_run_emits_exactly_once(self):
        data_manager = Mock()
        data_manager.refresh_portfolio.side_effect = [
            (
                True,
                {
                    "sequence": 1,
                },
            ),
            (
                False,
                "second failure",
            ),
        ]
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        worker.run()
        worker.run()

        self.assertEqual(
            emissions,
            [
                (
                    True,
                    {
                        "sequence": 1,
                    },
                ),
                (
                    False,
                    "second failure",
                ),
            ],
        )
        self.assertEqual(
            data_manager.refresh_portfolio.call_count,
            2,
        )

    def test_empty_exception_message_is_emitted(self):
        data_manager = Mock()
        data_manager.refresh_portfolio.side_effect = (
            RuntimeError()
        )
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        worker.run()

        self.assertEqual(
            emissions,
            [
                (
                    False,
                    "",
                )
            ],
        )

    def test_malformed_manager_result_is_contained(
        self,
    ):
        data_manager = Mock()
        data_manager.refresh_portfolio.return_value = (
            True,
        )
        worker = PortfolioRefreshWorker(
            data_manager
        )
        emissions = self.collect_emissions(worker)

        worker.run()

        self.assertEqual(len(emissions), 1)
        self.assertFalse(emissions[0][0])
        self.assertIsInstance(
            emissions[0][1],
            str,
        )
        self.assertIn(
            "unpack",
            emissions[0][1].lower(),
        )

    def test_signal_can_notify_multiple_listeners(self):
        data_manager = Mock()
        data_manager.refresh_portfolio.return_value = (
            True,
            "done",
        )
        worker = PortfolioRefreshWorker(
            data_manager
        )
        first_listener = []
        second_listener = []

        worker.result_ready.connect(
            lambda success, result: (
                first_listener.append(
                    (success, result)
                )
            )
        )
        worker.result_ready.connect(
            lambda success, result: (
                second_listener.append(
                    (success, result)
                )
            )
        )

        worker.run()

        expected = [
            (
                True,
                "done",
            )
        ]
        self.assertEqual(
            first_listener,
            expected,
        )
        self.assertEqual(
            second_listener,
            expected,
        )


if __name__ == "__main__":
    unittest.main()
