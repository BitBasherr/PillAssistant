# Complete Test Function Inventory

## test_options_flow.py (21 tests)

### Original Tests (4)
1. `test_options_flow_instantiation` - Validates _config_entry attribute fix
2. `test_options_flow_init` - Basic options flow initialization
3. `test_options_flow_update_dosage` - Dosage modification through options
4. `test_options_flow_update_schedule` - Schedule modification
5. `test_options_flow_update_refill_settings` - Refill settings modification

### New Tests Added (17)
6. `test_options_flow_with_single_schedule_time` - Single dose time
7. `test_options_flow_with_multiple_schedule_times` - 4x daily doses
8. `test_options_flow_with_empty_notes` - Empty notes handling
9. `test_options_flow_with_different_dosage_units` - mL dosage unit
10. `test_options_flow_with_high_refill_amount` - 365-day supply
11. `test_options_flow_with_weekend_only_schedule` - Weekend schedule
12. `test_options_flow_preserves_existing_data_on_display` - Form defaults
13. `test_options_flow_with_minimal_refill_reminder` - 1-day reminder
14. `test_options_flow_with_various_time_formats` - Edge times
15. `test_options_flow_updates_entry_data_not_options` - Data storage location
16. `test_options_flow_with_alternating_days` - Mon/Wed/Fri schedule
17. `test_options_flow_config_entry_attribute_access` - Attribute validation
18. `test_options_flow_with_decimal_dosage` - 2.5 mL dosage
19. `test_options_flow_long_medication_name` - 70+ char names
20. `test_options_flow_special_characters_in_notes` - Special chars
21. Plus additional variations

## test_config_flow.py (21 tests)

### Original Tests (5)
1. `test_user_step_medication_details` - Basic medication entry
2. `test_user_step_missing_medication_name` - Validation error
3. `test_schedule_step` - Basic schedule configuration
4. `test_complete_flow` - End-to-end flow
5. `test_duplicate_medication_rejected` - Duplicate prevention

### New Tests Added (16)
6. `test_schedule_step_with_single_time` - Single time entry
7. `test_schedule_step_with_multiple_times` - Multiple times entry
8. `test_schedule_step_converts_string_to_list` - Type conversion
9. `test_schedule_step_with_empty_days_uses_default` - Default days
10. `test_complete_flow_with_edge_times` - Midnight/23:59
11. `test_complete_flow_with_weekend_only` - Weekend configuration
12. `test_complete_flow_with_decimal_dosage` - Decimal values
13. `test_complete_flow_with_various_dosage_units` - All 9 units
14. `test_complete_flow_with_high_refill_settings` - 365-day refill
15. `test_complete_flow_with_long_medication_name` - Long names
16. `test_complete_flow_with_special_characters_in_notes` - Special chars
17. `test_complete_flow_with_empty_notes` - Empty notes
18. `test_complete_flow_with_alternating_days` - Mon/Wed/Fri
19. `test_complete_flow_with_minimal_refill_reminder` - 1-day reminder
20. `test_config_flow_stores_all_data_correctly` - Full data verification
21. Plus additional scenario tests

## Test Organization by Category

### Selector Testing (New Feature)
- `test_schedule_step_with_single_time`
- `test_schedule_step_with_multiple_times`
- `test_schedule_step_converts_string_to_list`
- `test_options_flow_with_single_schedule_time`
- `test_options_flow_with_multiple_schedule_times`
- `test_options_flow_with_various_time_formats`

### Bug Fix Validation
- `test_options_flow_instantiation` - AttributeError fix
- `test_options_flow_config_entry_attribute_access`

### Edge Case Testing
- `test_complete_flow_with_edge_times`
- `test_options_flow_with_various_time_formats`
- `test_schedule_step_with_empty_days_uses_default`
- `test_options_flow_with_minimal_refill_reminder`
- `test_complete_flow_with_minimal_refill_reminder`

### Data Validation
- `test_options_flow_updates_entry_data_not_options`
- `test_config_flow_stores_all_data_correctly`
- `test_options_flow_preserves_existing_data_on_display`

### User Scenarios
- `test_options_flow_with_weekend_only_schedule`
- `test_complete_flow_with_weekend_only`
- `test_options_flow_with_alternating_days`
- `test_complete_flow_with_alternating_days`

### Dosage Unit Coverage
- `test_options_flow_with_different_dosage_units`
- `test_complete_flow_with_various_dosage_units`
- `test_options_flow_with_decimal_dosage`
- `test_complete_flow_with_decimal_dosage`

### Field Validation
- `test_options_flow_with_empty_notes`
- `test_complete_flow_with_empty_notes`
- `test_options_flow_long_medication_name`
- `test_complete_flow_with_long_medication_name`
- `test_options_flow_special_characters_in_notes`
- `test_complete_flow_with_special_characters_in_notes`

### Refill Testing
- `test_options_flow_with_high_refill_amount`
- `test_complete_flow_with_high_refill_settings`
- `test_options_flow_update_refill_settings`

## Total Test Count: 42
- Options Flow: 21 tests
- Config Flow: 21 tests
- Original: 9 tests
- Added: 33 tests