# HomeOps durable journal: independent test execution

Operation: `HOMEOPS-DURABLE-JOURNAL-6F2C-20260917`. Existing work item: HomeOps issue #2; implementation carrier: PR #3.

Executed September 19, 2026 by ZZ–Trellis independent test support, Codex / GPT family. This record preserves the accepted full-suite executions and the original HomeOps product, domain-engine and submission lineage.

## Accepted result

| Execution | Tests | Result | unittest duration | Outer process duration |
| --- | ---: | --- | ---: | ---: |
| Normal Python | 79 | PASS, exit 0 | 8.966 seconds | 9.163 seconds |
| Actual optimized Python (`-O`) | 79 | PASS, exit 0 | 10.381 seconds | 10.899 seconds |

The 79 tests comprise **36 unchanged original tests** in `test_homeops.py` and `test_mcp_server.py`, plus **43 new independent tests**: 34 in `test_storage.py` and 9 in `test_durable_server.py`.

Both full-suite runs passed on their first execution. No source or expectation fixes occurred between the accepted runs. All seven source/test pins below matched before execution, after the normal run, and after the optimized run. This document was assembled from retained logs; authoring it did not rerun tests.

## Exact environment and commands

Working directory: `/workspace/scratch/02152e3a5897/homeops`, an ephemeral cloud source snapshot.

- Interpreter: `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python`
- Python: `3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]`
- SQLite: `3.53.1`
- Platform: `Linux-6.18.44-x86_64-with-glibc2.39`

Exact commands, run sequentially from that working directory:

```sh
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -B -m unittest discover -s tests -v
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python -B -O -m unittest discover -s tests -v
```

The process harness captured stdout and stderr together in each complete log. Test subprocess commands explicitly propagate the parent's optimization level. Concurrent worker results and the bounded backup-contention child also report and assert their actual `sys.flags.optimize`; the optimized run does not rely on an optimized parent silently launching normal worker children.

## Source binding

Git blob IDs include Git's length-prefixed object header. SHA-256 values cover the exact file bytes.

| Path | Bytes | Git blob SHA-1 | SHA-256 |
| --- | ---: | --- | --- |
| `homeops_relay/homeops.py` | 25224 | `6eb76d4bf4a1bedd211afbf715ea17018a3d7ad4` | `08848754c376e24f7bbd4b279dae918bb8468a2184078794984bebab06ea95da` |
| `homeops_relay/storage.py` | 21660 | `f49957091ba8bc10f2c2f4500b8fd833f29e8e2a` | `dd27ee20108f5f3ab5f7ea150e878729059aaabc98c0935af60e156da794c0d8` |
| `homeops_relay/mcp_server.py` | 20463 | `1edc1723736129beb84de348400ca3999383e92e` | `a5a2529b1c4cb0db4b426a35840d44e83c16f46813d60b0a7c1f45ea27e9a445` |
| `tests/test_homeops.py` | 6250 | `1c4af9f946de104302a4e38c4ee5b62978ee3fda` | `762baf2bb061a884b521b01e19f975fe389ab9ca5c4d3c87530372257b2d508f` |
| `tests/test_mcp_server.py` | 13558 | `2c1745e4d68416245b19365b590830229acb763e` | `7284bf1449443a67e6df02e2ef9c8e7ef66cab4881ae26390806d0b66698a3c4` |
| `tests/test_storage.py` | 28436 | `dcead3715d1a4fe93ad01a4e82c06b4480b2f265` | `4767493fdcd612d7064734a997fc41514c9944697d71a8b63ed523e8329c681a` |
| `tests/test_durable_server.py` | 12212 | `a0052b0bedb96333d6b56f82036dae4dd37716d9` | `78add17dec35ed5e5ae4d278e4647d98760e19d0f43b843d615963b4daf3e313` |

## Material cases actually covered

- Original domain equivalence for the complete four-mutation issue → quote → action proposal → owner-decision journey. Replay retains `APPROVED_NOT_EXECUTED`; all external-effect flags remain false.
- Historical exact retry returns the original response and receipt after later operations change the current journal receipt. Canonical key ordering is immaterial; changed supplied values and reuse across mutation names fail without appending.
- Real separate-process writers: six distinct operations produce one contiguous verified event chain; six exact retries append once and return the same response; two changed requests sharing an ID produce one winner and one conflict.
- Restart through the actual environment-configured HTTP server creates a fresh MCP session while preserving the committed operation and exact retry response. HTTP tool schemas advertise the mutation retry key; original ephemeral library behavior remains intact.
- A child exits with `os._exit(73)` immediately after a real SQLite commit and before a tool response. Reopening and retrying returns the original response with one event.
- A child performs a large valid domain mutation with SQLite cache spilling enabled, then exits with `os._exit(71)` before commit. A real nonzero hot rollback-journal header is verified before reopening. Recovery restores the exact prior inspection and historical retry; retrying the interrupted operation then appends exactly once.
- Narrow connection proxies inject exceptions immediately before and after real commit. Both report uncertainty, and exact retries recover without assuming that an acknowledgement error proves rollback. A real competing write lock fails without success or append and permits retry after release.
- Each call reloads committed state across existing adapters. Canonical stored command, event and response divergence is rejected, along with sequence changes, duplicate JSON keys, foreign schema/version and live corruption before retries or new mutations. The command/event/response edits preserve canonical JSON, so these checks reach semantic cross-validation.
- Actual retained boundaries: 10,001 rows and 67.5 MiB of aggregate retained JSON text are refused before replay. Request size, excessive JSON depth, cycles, non-finite values and invalid Unicode are refused without an operation.
- Backup/restore retains retry history and creates an independent journal. Existing destinations and the source are never overwritten. A real exclusive destination lock exercises the configured 0.05-second backup timeout in a bounded subprocess; failure preserves the source and removes the owned failed destination.
- Missing SQLite runtime-limit support and invalid timeouts, including a huge integer, are contained before database creation.
- Durable storage failures become structured MCP tool errors. Corrupt-journal health checks return complete HTTP 503 JSON before any success header.

## Scope and limits

This is source-bound local execution on the environment above. The suite uses real local SQLite, local HTTP servers and separate processes with synthetic data. Fault injection is confined to test-side connection wrappers and process exits; there are no production test hooks.

These runs are not hosted-provider CI, a Python-version or operating-system matrix, a power-loss/hardware durability guarantee, a remote filesystem qualification, a deployment, or competition-submission evidence. The separate operator rehearsal has its own execution record. This record does not itself assert that PR #3 has merged.

No provider contact, scheduling, purchase, household-system action, warranty submission or payment occurred.

## Complete normal execution log

The following block preserves the complete combined stdout/stderr log, including its command and environment header.

```text
Command: ['/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v']
Python: 3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]
SQLite: 3.53.1
Platform: Linux-6.18.44-x86_64-with-glibc2.39

test_ambiguous_ledger_and_path_fail_before_socket_bind (test_durable_server.DurableDispatcherTests.test_ambiguous_ledger_and_path_fail_before_socket_bind) ... ok
test_changed_operation_reuse_is_a_tool_error_without_second_event (test_durable_server.DurableDispatcherTests.test_changed_operation_reuse_is_a_tool_error_without_second_event) ... ok
test_durable_tools_list_advertises_required_operation_id (test_durable_server.DurableDispatcherTests.test_durable_tools_list_advertises_required_operation_id) ... ok
test_explicit_library_configuration_ignores_environment (test_durable_server.DurableDispatcherTests.test_explicit_library_configuration_ignores_environment) ... ok
test_storage_errors_are_structured_tool_errors (test_durable_server.DurableDispatcherTests.test_storage_errors_are_structured_tool_errors) ... ok
test_http_health_corruption_returns_complete_503_json (test_durable_server.DurableHTTPTests.test_http_health_corruption_returns_complete_503_json) ... ok
test_http_live_corruption_is_tool_error_without_journal_append (test_durable_server.DurableHTTPTests.test_http_live_corruption_is_tool_error_without_journal_append) ... ok
test_http_schema_retry_and_stored_original_response (test_durable_server.DurableHTTPTests.test_http_schema_retry_and_stored_original_response) ... ok
test_environment_configured_http_process_restart_preserves_retries (test_durable_server.DurableServerProcessTests.test_environment_configured_http_process_restart_preserves_retries) ... ok
test_action_cannot_be_reviewed_twice (test_homeops.LedgerTests.test_action_cannot_be_reviewed_twice) ... ok
test_action_is_proposal_only (test_homeops.LedgerTests.test_action_is_proposal_only) ... ok
test_bool_is_not_money (test_homeops.LedgerTests.test_bool_is_not_money) ... ok
test_chain_reordering_is_detected (test_homeops.LedgerTests.test_chain_reordering_is_detected) ... ok
test_deterministic_receipt_for_same_sequence (test_homeops.LedgerTests.test_deterministic_receipt_for_same_sequence) ... ok
test_evidence_cap (test_homeops.LedgerTests.test_evidence_cap) ... ok
test_invalid_event_kind_rejected_even_with_rehashed_event (test_homeops.LedgerTests.test_invalid_event_kind_rejected_even_with_rehashed_event) ... ok
test_quote_comparison_is_deterministic (test_homeops.LedgerTests.test_quote_comparison_is_deterministic) ... ok
test_replay_preserves_state_exactly (test_homeops.LedgerTests.test_replay_preserves_state_exactly) ... ok
test_snapshot_digest_changes_with_event (test_homeops.LedgerTests.test_snapshot_digest_changes_with_event) ... ok
test_tamper_is_detected (test_homeops.LedgerTests.test_tamper_is_detected) ... ok
test_unknown_argument_fails_closed (test_homeops.LedgerTests.test_unknown_argument_fails_closed) ... ok
test_unknown_issue_rejected (test_homeops.LedgerTests.test_unknown_issue_rejected) ... ok
test_urgent_plan_starts_with_safety (test_homeops.LedgerTests.test_urgent_plan_starts_with_safety) ... ok
test_duplicate_json_key_rejected (test_mcp_server.DispatcherTests.test_duplicate_json_key_rejected) ... ok
test_initialize_negotiates_back_to_server_version (test_mcp_server.DispatcherTests.test_initialize_negotiates_back_to_server_version) ... ok
test_initialize_negotiates_required_protocol (test_mcp_server.DispatcherTests.test_initialize_negotiates_required_protocol) ... ok
test_initialize_rejects_missing_client_info (test_mcp_server.DispatcherTests.test_initialize_rejects_missing_client_info) ... ok
test_nonfinite_json_rejected (test_mcp_server.DispatcherTests.test_nonfinite_json_rejected) ... ok
test_notification_has_no_response (test_mcp_server.DispatcherTests.test_notification_has_no_response) ... ok
test_tool_validation_error_is_mcp_tool_error (test_mcp_server.DispatcherTests.test_tool_validation_error_is_mcp_tool_error) ... ok
test_tools_list_exposes_runtime_tools_and_accepts_null_cursor (test_mcp_server.DispatcherTests.test_tools_list_exposes_runtime_tools_and_accepts_null_cursor) ... ok
test_tools_list_rejects_unissued_cursor (test_mcp_server.DispatcherTests.test_tools_list_rejects_unissued_cursor) ... ok
test_unknown_rpc_method (test_mcp_server.DispatcherTests.test_unknown_rpc_method) ... ok
test_delete_session (test_mcp_server.HttpTests.test_delete_session) ... ok
test_end_to_end_tool_call (test_mcp_server.HttpTests.test_end_to_end_tool_call) ... ok
test_healthz (test_mcp_server.HttpTests.test_healthz) ... ok
test_http_initialize_creates_secure_session (test_mcp_server.HttpTests.test_http_initialize_creates_secure_session) ... ok
test_local_origin_allowed (test_mcp_server.HttpTests.test_local_origin_allowed) ... ok
test_mcp_get_is_method_not_allowed_and_origin_checked (test_mcp_server.HttpTests.test_mcp_get_is_method_not_allowed_and_origin_checked) ... ok
test_origin_rejected (test_mcp_server.HttpTests.test_origin_rejected) ... ok
test_post_requires_both_accept_types (test_mcp_server.HttpTests.test_post_requires_both_accept_types) ... ok
test_rate_limit_is_session_scoped_and_fail_closed (test_mcp_server.HttpTests.test_rate_limit_is_session_scoped_and_fail_closed) ... ok
test_subsequent_request_requires_session_and_protocol_headers (test_mcp_server.HttpTests.test_subsequent_request_requires_session_and_protocol_headers) ... ok
test_tools_blocked_until_initialized_notification (test_mcp_server.HttpTests.test_tools_blocked_until_initialized_notification) ... ok
test_unknown_session_is_404 (test_mcp_server.HttpTests.test_unknown_session_is_404) ... ok
test_backup_destination_contention_respects_timeout_and_cleans_owned_file (test_storage.JournalTests.test_backup_destination_contention_respects_timeout_and_cleans_owned_file) ... ok
test_backup_never_overwrites_existing_destination_or_source (test_storage.JournalTests.test_backup_never_overwrites_existing_destination_or_source) ... ok
test_backup_restore_keeps_retry_journal_and_is_independent (test_storage.JournalTests.test_backup_restore_keeps_retry_journal_and_is_independent) ... ok
test_canonical_mapping_order_is_an_exact_retry (test_storage.JournalTests.test_canonical_mapping_order_is_an_exact_retry) ... ok
test_changed_reuse_rejects_without_append_even_when_domain_normalizes_same (test_storage.JournalTests.test_changed_reuse_rejects_without_append_even_when_domain_normalizes_same) ... ok
test_commit_exception_after_real_commit_is_uncertain_and_retry_deduplicates (test_storage.JournalTests.test_commit_exception_after_real_commit_is_uncertain_and_retry_deduplicates) ... ok
test_commit_exception_before_commit_rolls_back_and_same_key_can_retry (test_storage.JournalTests.test_commit_exception_before_commit_rolls_back_and_same_key_can_retry) ... ok
test_concurrent_process_changed_reuse_has_one_winner (test_storage.JournalTests.test_concurrent_process_changed_reuse_has_one_winner) ... ok
test_concurrent_process_distinct_operations_form_one_contiguous_chain (test_storage.JournalTests.test_concurrent_process_distinct_operations_form_one_contiguous_chain) ... ok
test_concurrent_process_exact_retries_append_once (test_storage.JournalTests.test_concurrent_process_exact_retries_append_once) ... ok
test_corrupt_event_response_request_and_sequence_are_each_refused (test_storage.JournalTests.test_corrupt_event_response_request_and_sequence_are_each_refused) ... ok
test_create_false_missing_path_and_empty_file_are_refused (test_storage.JournalTests.test_create_false_missing_path_and_empty_file_are_refused) ... ok
test_domain_failure_does_not_consume_retry_key (test_storage.JournalTests.test_domain_failure_does_not_consume_retry_key) ... ok
test_duplicate_stored_json_keys_are_refused (test_storage.JournalTests.test_duplicate_stored_json_keys_are_refused) ... ok
test_durable_tool_schemas_change_only_mutation_operation_ids (test_storage.JournalTests.test_durable_tool_schemas_change_only_mutation_operation_ids) ... ok
test_empty_journal_matches_original_domain (test_storage.JournalTests.test_empty_journal_matches_original_domain) ... ok
test_foreign_schema_and_changed_version_are_refused (test_storage.JournalTests.test_foreign_schema_and_changed_version_are_refused) ... ok
test_four_mutation_journey_matches_domain_and_replays_after_restart (test_storage.JournalTests.test_four_mutation_journey_matches_domain_and_replays_after_restart) ... ok
test_invalid_timeout_including_huge_integer_is_contained_before_creation (test_storage.JournalTests.test_invalid_timeout_including_huge_integer_is_contained_before_creation) ... ok
test_live_corruption_is_reloaded_before_retry_or_new_write (test_storage.JournalTests.test_live_corruption_is_reloaded_before_retry_or_new_write) ... ok
test_locked_writer_fails_without_success_or_append_then_retry_works (test_storage.JournalTests.test_locked_writer_fails_without_success_or_append_then_retry_works) ... ok
test_missing_runtime_limit_api_refused_before_database_creation (test_storage.JournalTests.test_missing_runtime_limit_api_refused_before_database_creation) ... ok
test_mutations_require_valid_operation_ids (test_storage.JournalTests.test_mutations_require_valid_operation_ids) ... ok
test_old_retry_returns_original_response_after_later_event (test_storage.JournalTests.test_old_retry_returns_original_response_after_later_event) ... ok
test_operation_id_is_global_across_mutation_names (test_storage.JournalTests.test_operation_id_is_global_across_mutation_names) ... ok
test_process_exit_immediately_after_commit_recovers_same_response (test_storage.JournalTests.test_process_exit_immediately_after_commit_recovers_same_response) ... ok
test_process_restart_recovers_exact_response (test_storage.JournalTests.test_process_restart_recovers_exact_response) ... ok
test_reads_reject_operation_ids_and_do_not_add_operations (test_storage.JournalTests.test_reads_reject_operation_ids_and_do_not_add_operations) ... ok
test_request_size_depth_cycles_and_nonfinite_fail_without_append (test_storage.JournalTests.test_request_size_depth_cycles_and_nonfinite_fail_without_append) ... ok
test_retained_bytes_above_sixty_four_mib_refused_before_json_decode (test_storage.JournalTests.test_retained_bytes_above_sixty_four_mib_refused_before_json_decode) ... ok
test_retained_event_count_above_ten_thousand_refused_before_replay (test_storage.JournalTests.test_retained_event_count_above_ten_thousand_refused_before_replay) ... ok
test_returned_values_are_detached_from_persisted_journal (test_storage.JournalTests.test_returned_values_are_detached_from_persisted_journal) ... ok
test_two_existing_instances_reload_each_call (test_storage.JournalTests.test_two_existing_instances_reload_each_call) ... ok
test_uncommitted_spill_crash_recovers_hot_journal_before_replay (test_storage.JournalTests.test_uncommitted_spill_crash_recovers_hot_journal_before_replay) ... ok

----------------------------------------------------------------------
Ran 79 tests in 8.966s

OK
```

## Complete optimized execution log

The following block preserves the complete combined stdout/stderr log for the actual `-O` command.

```text
Command: ['/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python', '-B', '-O', '-m', 'unittest', 'discover', '-s', 'tests', '-v']
Python: 3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]
SQLite: 3.53.1
Platform: Linux-6.18.44-x86_64-with-glibc2.39

test_ambiguous_ledger_and_path_fail_before_socket_bind (test_durable_server.DurableDispatcherTests.test_ambiguous_ledger_and_path_fail_before_socket_bind) ... ok
test_changed_operation_reuse_is_a_tool_error_without_second_event (test_durable_server.DurableDispatcherTests.test_changed_operation_reuse_is_a_tool_error_without_second_event) ... ok
test_durable_tools_list_advertises_required_operation_id (test_durable_server.DurableDispatcherTests.test_durable_tools_list_advertises_required_operation_id) ... ok
test_explicit_library_configuration_ignores_environment (test_durable_server.DurableDispatcherTests.test_explicit_library_configuration_ignores_environment) ... ok
test_storage_errors_are_structured_tool_errors (test_durable_server.DurableDispatcherTests.test_storage_errors_are_structured_tool_errors) ... ok
test_http_health_corruption_returns_complete_503_json (test_durable_server.DurableHTTPTests.test_http_health_corruption_returns_complete_503_json) ... ok
test_http_live_corruption_is_tool_error_without_journal_append (test_durable_server.DurableHTTPTests.test_http_live_corruption_is_tool_error_without_journal_append) ... ok
test_http_schema_retry_and_stored_original_response (test_durable_server.DurableHTTPTests.test_http_schema_retry_and_stored_original_response) ... ok
test_environment_configured_http_process_restart_preserves_retries (test_durable_server.DurableServerProcessTests.test_environment_configured_http_process_restart_preserves_retries) ... ok
test_action_cannot_be_reviewed_twice (test_homeops.LedgerTests.test_action_cannot_be_reviewed_twice) ... ok
test_action_is_proposal_only (test_homeops.LedgerTests.test_action_is_proposal_only) ... ok
test_bool_is_not_money (test_homeops.LedgerTests.test_bool_is_not_money) ... ok
test_chain_reordering_is_detected (test_homeops.LedgerTests.test_chain_reordering_is_detected) ... ok
test_deterministic_receipt_for_same_sequence (test_homeops.LedgerTests.test_deterministic_receipt_for_same_sequence) ... ok
test_evidence_cap (test_homeops.LedgerTests.test_evidence_cap) ... ok
test_invalid_event_kind_rejected_even_with_rehashed_event (test_homeops.LedgerTests.test_invalid_event_kind_rejected_even_with_rehashed_event) ... ok
test_quote_comparison_is_deterministic (test_homeops.LedgerTests.test_quote_comparison_is_deterministic) ... ok
test_replay_preserves_state_exactly (test_homeops.LedgerTests.test_replay_preserves_state_exactly) ... ok
test_snapshot_digest_changes_with_event (test_homeops.LedgerTests.test_snapshot_digest_changes_with_event) ... ok
test_tamper_is_detected (test_homeops.LedgerTests.test_tamper_is_detected) ... ok
test_unknown_argument_fails_closed (test_homeops.LedgerTests.test_unknown_argument_fails_closed) ... ok
test_unknown_issue_rejected (test_homeops.LedgerTests.test_unknown_issue_rejected) ... ok
test_urgent_plan_starts_with_safety (test_homeops.LedgerTests.test_urgent_plan_starts_with_safety) ... ok
test_duplicate_json_key_rejected (test_mcp_server.DispatcherTests.test_duplicate_json_key_rejected) ... ok
test_initialize_negotiates_back_to_server_version (test_mcp_server.DispatcherTests.test_initialize_negotiates_back_to_server_version) ... ok
test_initialize_negotiates_required_protocol (test_mcp_server.DispatcherTests.test_initialize_negotiates_required_protocol) ... ok
test_initialize_rejects_missing_client_info (test_mcp_server.DispatcherTests.test_initialize_rejects_missing_client_info) ... ok
test_nonfinite_json_rejected (test_mcp_server.DispatcherTests.test_nonfinite_json_rejected) ... ok
test_notification_has_no_response (test_mcp_server.DispatcherTests.test_notification_has_no_response) ... ok
test_tool_validation_error_is_mcp_tool_error (test_mcp_server.DispatcherTests.test_tool_validation_error_is_mcp_tool_error) ... ok
test_tools_list_exposes_runtime_tools_and_accepts_null_cursor (test_mcp_server.DispatcherTests.test_tools_list_exposes_runtime_tools_and_accepts_null_cursor) ... ok
test_tools_list_rejects_unissued_cursor (test_mcp_server.DispatcherTests.test_tools_list_rejects_unissued_cursor) ... ok
test_unknown_rpc_method (test_mcp_server.DispatcherTests.test_unknown_rpc_method) ... ok
test_delete_session (test_mcp_server.HttpTests.test_delete_session) ... ok
test_end_to_end_tool_call (test_mcp_server.HttpTests.test_end_to_end_tool_call) ... ok
test_healthz (test_mcp_server.HttpTests.test_healthz) ... ok
test_http_initialize_creates_secure_session (test_mcp_server.HttpTests.test_http_initialize_creates_secure_session) ... ok
test_local_origin_allowed (test_mcp_server.HttpTests.test_local_origin_allowed) ... ok
test_mcp_get_is_method_not_allowed_and_origin_checked (test_mcp_server.HttpTests.test_mcp_get_is_method_not_allowed_and_origin_checked) ... ok
test_origin_rejected (test_mcp_server.HttpTests.test_origin_rejected) ... ok
test_post_requires_both_accept_types (test_mcp_server.HttpTests.test_post_requires_both_accept_types) ... ok
test_rate_limit_is_session_scoped_and_fail_closed (test_mcp_server.HttpTests.test_rate_limit_is_session_scoped_and_fail_closed) ... ok
test_subsequent_request_requires_session_and_protocol_headers (test_mcp_server.HttpTests.test_subsequent_request_requires_session_and_protocol_headers) ... ok
test_tools_blocked_until_initialized_notification (test_mcp_server.HttpTests.test_tools_blocked_until_initialized_notification) ... ok
test_unknown_session_is_404 (test_mcp_server.HttpTests.test_unknown_session_is_404) ... ok
test_backup_destination_contention_respects_timeout_and_cleans_owned_file (test_storage.JournalTests.test_backup_destination_contention_respects_timeout_and_cleans_owned_file) ... ok
test_backup_never_overwrites_existing_destination_or_source (test_storage.JournalTests.test_backup_never_overwrites_existing_destination_or_source) ... ok
test_backup_restore_keeps_retry_journal_and_is_independent (test_storage.JournalTests.test_backup_restore_keeps_retry_journal_and_is_independent) ... ok
test_canonical_mapping_order_is_an_exact_retry (test_storage.JournalTests.test_canonical_mapping_order_is_an_exact_retry) ... ok
test_changed_reuse_rejects_without_append_even_when_domain_normalizes_same (test_storage.JournalTests.test_changed_reuse_rejects_without_append_even_when_domain_normalizes_same) ... ok
test_commit_exception_after_real_commit_is_uncertain_and_retry_deduplicates (test_storage.JournalTests.test_commit_exception_after_real_commit_is_uncertain_and_retry_deduplicates) ... ok
test_commit_exception_before_commit_rolls_back_and_same_key_can_retry (test_storage.JournalTests.test_commit_exception_before_commit_rolls_back_and_same_key_can_retry) ... ok
test_concurrent_process_changed_reuse_has_one_winner (test_storage.JournalTests.test_concurrent_process_changed_reuse_has_one_winner) ... ok
test_concurrent_process_distinct_operations_form_one_contiguous_chain (test_storage.JournalTests.test_concurrent_process_distinct_operations_form_one_contiguous_chain) ... ok
test_concurrent_process_exact_retries_append_once (test_storage.JournalTests.test_concurrent_process_exact_retries_append_once) ... ok
test_corrupt_event_response_request_and_sequence_are_each_refused (test_storage.JournalTests.test_corrupt_event_response_request_and_sequence_are_each_refused) ... ok
test_create_false_missing_path_and_empty_file_are_refused (test_storage.JournalTests.test_create_false_missing_path_and_empty_file_are_refused) ... ok
test_domain_failure_does_not_consume_retry_key (test_storage.JournalTests.test_domain_failure_does_not_consume_retry_key) ... ok
test_duplicate_stored_json_keys_are_refused (test_storage.JournalTests.test_duplicate_stored_json_keys_are_refused) ... ok
test_durable_tool_schemas_change_only_mutation_operation_ids (test_storage.JournalTests.test_durable_tool_schemas_change_only_mutation_operation_ids) ... ok
test_empty_journal_matches_original_domain (test_storage.JournalTests.test_empty_journal_matches_original_domain) ... ok
test_foreign_schema_and_changed_version_are_refused (test_storage.JournalTests.test_foreign_schema_and_changed_version_are_refused) ... ok
test_four_mutation_journey_matches_domain_and_replays_after_restart (test_storage.JournalTests.test_four_mutation_journey_matches_domain_and_replays_after_restart) ... ok
test_invalid_timeout_including_huge_integer_is_contained_before_creation (test_storage.JournalTests.test_invalid_timeout_including_huge_integer_is_contained_before_creation) ... ok
test_live_corruption_is_reloaded_before_retry_or_new_write (test_storage.JournalTests.test_live_corruption_is_reloaded_before_retry_or_new_write) ... ok
test_locked_writer_fails_without_success_or_append_then_retry_works (test_storage.JournalTests.test_locked_writer_fails_without_success_or_append_then_retry_works) ... ok
test_missing_runtime_limit_api_refused_before_database_creation (test_storage.JournalTests.test_missing_runtime_limit_api_refused_before_database_creation) ... ok
test_mutations_require_valid_operation_ids (test_storage.JournalTests.test_mutations_require_valid_operation_ids) ... ok
test_old_retry_returns_original_response_after_later_event (test_storage.JournalTests.test_old_retry_returns_original_response_after_later_event) ... ok
test_operation_id_is_global_across_mutation_names (test_storage.JournalTests.test_operation_id_is_global_across_mutation_names) ... ok
test_process_exit_immediately_after_commit_recovers_same_response (test_storage.JournalTests.test_process_exit_immediately_after_commit_recovers_same_response) ... ok
test_process_restart_recovers_exact_response (test_storage.JournalTests.test_process_restart_recovers_exact_response) ... ok
test_reads_reject_operation_ids_and_do_not_add_operations (test_storage.JournalTests.test_reads_reject_operation_ids_and_do_not_add_operations) ... ok
test_request_size_depth_cycles_and_nonfinite_fail_without_append (test_storage.JournalTests.test_request_size_depth_cycles_and_nonfinite_fail_without_append) ... ok
test_retained_bytes_above_sixty_four_mib_refused_before_json_decode (test_storage.JournalTests.test_retained_bytes_above_sixty_four_mib_refused_before_json_decode) ... ok
test_retained_event_count_above_ten_thousand_refused_before_replay (test_storage.JournalTests.test_retained_event_count_above_ten_thousand_refused_before_replay) ... ok
test_returned_values_are_detached_from_persisted_journal (test_storage.JournalTests.test_returned_values_are_detached_from_persisted_journal) ... ok
test_two_existing_instances_reload_each_call (test_storage.JournalTests.test_two_existing_instances_reload_each_call) ... ok
test_uncommitted_spill_crash_recovers_hot_journal_before_replay (test_storage.JournalTests.test_uncommitted_spill_crash_recovers_hot_journal_before_replay) ... ok

----------------------------------------------------------------------
Ran 79 tests in 10.381s

OK
```
