import unittest
from copy import deepcopy
from peerplays.event import Event
from bookied_sync import comparators
from bookied_sync.utils import dList2Dict
from bookied_sync.bettingmarketgroup import LookupBettingMarketGroup
from bookied_sync.bettingmarketgroupresolve import LookupBettingMarketGroupResolve
from peerplays.utils import parse_time
from .fixtures import fixture_data, config, lookup_test_event

event_id = "1.22.2242"
bmg_id = "1.24.218"
test_operation_dict = {
    "id": bmg_id,
    "description": [
        ["display_name", "Over/Under 3.5 pts"],
        ["en", "Over/Under 3.5 pts"],
        ["sen", "Total Points"],
        ["_dynamic", "ou"],
        ["_ou", "3.5"],
    ],
    "event_id": "0.0.0",
    "rules_id": "1.23.10",
    "asset_id": "1.3.0",
    "status": "ongoing",
}


class Testcases(unittest.TestCase):
    def setUp(self):
        fixture_data()
        self.lookup.set_overunder(3.5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fixture_data()

        event = lookup_test_event(event_id)
        self.lookup = list(event.bettingmarketgroups)[2]

    def test_init(self):
        self.assertIsInstance(self.lookup, LookupBettingMarketGroup)

    def test_rounding_overunder(self):
        self.lookup.set_overunder(3.1)
        self.assertIn(["en", "Over/Under 3.5 pts"], self.lookup.description)

    def test_set_handicap(self):
        self.assertEqual(self.lookup["overunder"], 3.5)

    def test_bmg_names(self):
        self.assertIn(["en", "Over/Under 3.5 pts"], self.lookup.description)

    def test_bms_names(self):
        bms = list(self.lookup.bettingmarkets)
        over = bms[0].description
        under = bms[1].description
        self.assertIn(["en", "Under 3.5"], over)
        self.assertIn(["en", "Over 3.5"], under)

    def test_test_operation_equal(self):
        self.assertTrue(self.lookup.test_operation_equal(test_operation_dict))

        with self.assertRaises(ValueError):
            self.assertTrue(self.lookup.test_operation_equal({}))

    def test_find_id(self):
        self.assertEqual(self.lookup.find_id(), bmg_id)

    def test_is_synced(self):
        self.lookup["id"] = bmg_id
        self.assertTrue(self.lookup.is_synced())

    def test_propose_new(self):
        from peerplaysbase.operationids import operations

        self.lookup.clear_proposal_buffer()
        tx = self.lookup.propose_new()
        tx = tx.json()
        self.assertIsInstance(tx, dict)
        self.assertIn("operations", tx)
        self.assertIn("ref_block_num", tx)
        self.assertEqual(tx["operations"][0][0], 22)
        self.assertEqual(
            tx["operations"][0][1]["proposed_ops"][0]["op"][0],
            operations[self.lookup.operation_create],
        )

    def test_propose_update(self):
        from peerplaysbase.operationids import operations

        self.lookup["id"] = bmg_id
        self.lookup.clear_proposal_buffer()
        tx = self.lookup.propose_update()
        tx = tx.json()
        self.assertIsInstance(tx, dict)
        self.assertIn("operations", tx)
        self.assertIn("ref_block_num", tx)
        self.assertEqual(tx["operations"][0][0], 22)
        self.assertEqual(
            tx["operations"][0][1]["proposed_ops"][0]["op"][0],
            operations[self.lookup.operation_update],
        )

    def assertResult(self, resolutions, *results):
        self.assertEqual(len(results), len(resolutions))
        for r in results:
            self.assertIn(r, resolutions)

    def test_result_00_on_35(self):
        resolve = LookupBettingMarketGroupResolve(self.lookup, [0, 0], overunder=3.5)
        self.assertEqual(resolve.metric, 0.0)
        self.assertResult(
            resolve.resolutions,
            ["1.25.2962", "not_win"],  # over
            ["1.25.2963", "win"],  # under
        )

    def test_result_10_on_35(self):
        resolve = LookupBettingMarketGroupResolve(self.lookup, [1, 0], overunder=3.5)
        self.assertEqual(resolve.metric, 1.0)
        self.assertResult(
            resolve.resolutions,
            ["1.25.2962", "not_win"],  # over
            ["1.25.2963", "win"],  # under
        )

    def test_result_11_on_35(self):
        resolve = LookupBettingMarketGroupResolve(self.lookup, [1, 1], overunder=3.5)
        self.assertEqual(resolve.metric, 2.0)
        self.assertResult(
            resolve.resolutions,
            ["1.25.2962", "not_win"],  # over
            ["1.25.2963", "win"],  # under
        )

    def test_result_12_on_35(self):
        resolve = LookupBettingMarketGroupResolve(self.lookup, [1, 2], overunder=3.5)
        self.assertEqual(resolve.metric, 3.0)
        self.assertResult(
            resolve.resolutions,
            ["1.25.2962", "not_win"],  # over
            ["1.25.2963", "win"],  # under
        )

    def test_result_22_on_35(self):
        resolve = LookupBettingMarketGroupResolve(self.lookup, [2, 2], overunder=3.5)
        self.assertEqual(resolve.metric, 4.0)
        self.assertResult(
            resolve.resolutions,
            ["1.25.2962", "win"],  # over
            ["1.25.2963", "not_win"],  # under
        )

    def test_result_20_on_15(self):
        resolve = LookupBettingMarketGroupResolve(self.lookup, [2, 0], overunder=1.5)
        self.assertEqual(resolve.metric, 2.0)
        self.assertResult(
            resolve.resolutions,
            ["1.25.2962", "win"],  # over
            ["1.25.2963", "not_win"],  # under
        )

    def test_result_10_on_15(self):
        resolve = LookupBettingMarketGroupResolve(self.lookup, [1, 0], overunder=1.5)
        self.assertEqual(resolve.metric, 1.0)
        self.assertResult(
            resolve.resolutions,
            ["1.25.2962", "not_win"],  # over
            ["1.25.2963", "win"],  # under
        )

    def test_find_fuzzy_market(self):
        self.assertEqual(
            self.lookup.find_id(
                find_id_search=[
                    lambda x, y: ["en", dList2Dict(x.description)["en"]]
                    in y["description"]
                ]
            ),
            "1.24.218",
        )

        self.assertEqual(
            self.lookup.find_id(find_id_search=[comparators.cmp_dynamic_bmg_fuzzy(0)]), "1.24.218"
        )

        # No match because   floor(4.9) + 0.5 = 4.5
        self.lookup.set_overunder(4.9)
        self.assertFalse(self.lookup.find_id(find_id_search=[comparators.cmp_dynamic_bmg_fuzzy(0)]))

        # Match!
        self.lookup.set_overunder(5.0)
        self.assertTrue(self.lookup.find_id(find_id_search=[comparators.cmp_dynamic_bmg_fuzzy(0)]))

        self.assertTrue(
            self.lookup.find_id(find_id_search=[comparators.cmp_dynamic_bmg_fuzzy(0.51)])
        )

    def test_fuzzy_operation_compare(self):
        self.assertTrue(
            self.lookup.test_operation_equal(
                test_operation_dict,
                test_operation_equal_search=[
                    comparators.cmp_required_keys(
                        ["description", "event_id", "rules_id"]
                    ),
                    comparators.cmp_status(),
                    comparators.cmp_event(),
                    comparators.cmp_all_description(),
                ],
            )
        )
        t2 = deepcopy(test_operation_dict)
        t2["description"] = [
            ["display_name", "Over/Under 3.5 pts"],
            ["en", "Over/Under 3.5 pts"],
            ["sen", "Total Points"],
            ["_dynamic", "FAKE"],
            ["_ou", "FAKE"],
        ]
        self.assertFalse(
            self.lookup.test_operation_equal(
                t2, test_operation_equal_search=[comparators.cmp_all_description()]
            )
        )
        self.assertTrue(
            self.lookup.test_operation_equal(
                t2,
                test_operation_equal_search=[
                    comparators.cmp_descriptions(["en", "display_name"])
                ],
            )
        )

        self.assertTrue(
            self.lookup.test_operation_equal(
                t2,
                test_operation_equal_search=[
                    comparators.cmp_langs("description", langs=lambda x: x[0] != "_")
                ],
            )
        )
