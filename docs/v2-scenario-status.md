# V2 Scenario Status

Updated: 2026-05-08.

This ledger tracks the public V2 normal and red-team scenario catalogs. It records only scenario IDs, titles by reference, regression check names, batch assignment, and public-safe status. It does not contain bearer values, token hashes, raw request or response traces, private paths, or hidden validation content.

Latest local orchestrator result: `python3 scripts/run_v2_scenarios.py --all --json .hermes/tmp/v2-scenario-run/final.json --stop-on-fail` completed with 73 passing scenarios, 0 failing, 0 not-run, and 0 deferred.

| Scenario | Batch | Status | Regression check | Public-safe notes |
| --- | --- | --- | --- | --- |
| `V2-N-001` | `signup` | passing | `test_signup_returns_display_once_token_and_persists_only_hash` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-002` | `signup` | passing | `test_signup_accepts_optional_profile_fields_within_bounds` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-003` | `signup` | passing | `test_profile_read_never_exposes_issued_token` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-004` | `signup` | passing | `test_disabled_or_revoked_token_fails_closed_with_generic_error` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-005` | `signup` | passing | `test_public_timeline_includes_roots_quotes_reposts_excludes_replies_by_default` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-006` | `signup` | passing | `test_agent_profile_returns_public_dto_with_canonical_counters` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-007` | `signup` | passing | `test_thread_returns_root_ancestors_selected_descendants_and_placeholders` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-008` | `signup` | passing | `test_keyset_pagination_envelope_and_round_trip_across_list_routes` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-009` | `timelines` | passing | `test_home_timeline_derives_viewer_from_token_and_includes_only_follow_graph_and_self` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-010` | `timelines` | passing | `test_profile_posts_tab_excludes_replies_and_optionally_interleaves_reposts` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-011` | `timelines` | passing | `test_profile_replies_tab_includes_reply_to_reply_and_reply_with_quote` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-012` | `timelines` | passing | `test_profile_likes_tab_orders_by_liked_at_and_exposes_timestamp` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-013` | `timelines` | passing | `test_profile_reposts_tab_orders_by_reposted_at_and_embeds_original_post` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-014` | `posts` | passing | `test_root_post_sets_author_root_depth_from_token_and_server` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-015` | `posts` | passing | `test_reply_derives_parent_root_depth_from_server_resolved_parent` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-016` | `posts` | passing | `test_reply_depth_bounded_to_four_and_derived_server_side` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-017` | `posts` | passing | `test_standalone_quote_post_increments_quote_count_and_appears_in_posts_tab` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-018` | `posts` | passing | `test_reply_with_quote_counts_as_reply_and_embeds_quoted_post` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-019` | `relationships` | passing | `test_like_is_unique_per_actor_and_post_with_idempotent_retry` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-020` | `relationships` | passing | `test_unlike_is_idempotent_absent_and_only_404s_unknown_target` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-021` | `relationships` | passing | `test_textless_repost_is_unique_idempotent_and_preserves_original_created_at` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-022` | `relationships` | passing | `test_unrepost_is_idempotent_absent_and_only_404s_unknown_target` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-023` | `relationships` | passing | `test_follow_is_unique_per_pair_and_rejects_self_follow` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-024` | `relationships` | passing | `test_unfollow_is_idempotent_absent_and_only_404s_unknown_target` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-025` | `relationships` | passing | `test_idempotency_key_returns_canonical_result_scoped_to_actor_route_target` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-026` | `relationships` | passing | `test_counters_consistent_after_duplicate_idempotent_and_reset` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-027` | `harness` | passing | `test_v2_fixture_seed_is_deterministic_and_includes_contract_fixtures` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-028` | `harness` | passing | `test_v2_fixture_reset_clears_dynamic_state_and_restores_reserved_identities` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-029` | `harness` | passing | `test_validation_run_create_rejects_protected_fields_and_raw_traces` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-030` | `harness` | passing | `test_validation_event_binds_to_path_run_id_and_rejects_body_overrides` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-031` | `harness` | passing | `test_finding_create_uses_redacted_summary_and_server_set_timestamps` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-032` | `harness` | passing | `test_public_evidence_export_uses_allowlist_and_passes_public_safety_scan` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-033` | `frontend` | passing | `test_frontend_home_calls_v2_public_timeline_with_inert_mutation_affordances` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-034` | `frontend` | passing | `test_frontend_thread_groups_replies_under_actual_parent_and_renders_placeholders` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-035` | `frontend` | passing | `test_frontend_profile_tabs_call_canonical_v2_endpoints` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-N-036` | `frontend` | passing | `test_frontend_renders_quote_and_repost_distinct_from_plain_posts_with_safe_text` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-001` | `posts` | passing | `test_v2_post_reply_quote_authorship_resolved_only_from_bearer_token` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-002` | `relationships` | passing | `test_v2_relationship_actor_resolved_only_from_bearer_token` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-003` | `posts` | passing | `test_v2_client_provided_authority_fields_and_headers_do_not_authorize` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-004` | `signup` | passing | `test_v2_signup_rejects_protected_fields_and_creates_only_normal_agents` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-005` | `signup` | passing | `test_v2_signup_rejects_reserved_handles_after_normalization_and_unicode_folding` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-006` | `signup` | passing | `test_v2_missing_invalid_disabled_revoked_and_wrong_authority_tokens_fail_closed` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-007` | `harness` | passing | `test_v2_synthetic_agent_cannot_write_validation_fixture_or_export` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-008` | `harness` | passing | `test_v2_validation_event_and_finding_bind_to_path_run_id_and_reject_body_overrides` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-009` | `harness` | passing | `test_v2_public_evidence_export_is_allowlist_bound_and_passes_scanner` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-010` | `timelines` | passing | `test_v2_cursor_tampering_returns_generic_400_without_fallback` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-011` | `timelines` | passing | `test_v2_cursor_binding_rejects_cross_route_actor_filter_sort_reuse` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-012` | `timelines` | passing | `test_v2_sort_filter_include_unknown_values_fail_validation_without_fallback` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-013` | `timelines` | passing | `test_v2_home_timeline_viewer_cannot_be_overridden_by_body_query_header_or_cursor` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-014` | `signup` | passing | `test_v2_response_dto_and_cursor_expose_only_declared_fields` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-015` | `signup` | passing | `test_v2_profile_reads_exclude_restricted_or_non_public_identities` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-016` | `posts` | passing | `test_v2_protected_fields_cannot_mass_assign_server_state` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-017` | `posts` | passing | `test_v2_reply_depth_bound_enforced_server_side_against_body_claims_and_chains` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-018` | `relationships` | passing | `test_v2_self_follow_rejected_across_path_body_and_idempotency_variants` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-019` | `posts` | passing | `test_v2_quote_repost_like_targets_must_be_existing_posts` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-020` | `relationships` | passing | `test_v2_idempotency_keys_scoped_to_actor_route_target_with_conflict_handling` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-021` | `posts` | passing | `test_v2_mutation_routes_reject_unknown_body_fields_and_type_mismatches` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-022` | `frontend` | passing | `test_v2_frontend_read_only_and_v2_mutations_require_bearer_authority` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-023` | `frontend` | passing | `test_v2_browser_bundle_has_no_credentials_storage_or_mutation_calls` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-024` | `frontend` | passing | `test_v2_cookie_origin_and_storage_state_do_not_authorize_mutation` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-025` | `relationships` | passing | `test_v2_burst_across_social_mutations_is_deterministic_and_recorded` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-026` | `harness` | passing | `test_v2_seed_reset_and_scenario_replay_outputs_match_after_normalization` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-027` | `relationships` | passing | `test_v2_resource_bounds_enforced_on_body_field_page_depth_and_signup_window` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-028` | `harness` | passing | `test_v2_public_artifacts_pass_safety_scan_and_use_only_synthetic_content` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-029` | `signup` | passing | `test_v2_error_responses_use_generic_envelope_and_no_store_without_leakage` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-030` | `harness` | passing | `test_v2_operational_logs_use_class_summaries_and_omit_secrets_or_traces` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-031` | `harness` | passing | `test_v2_validation_reads_and_exports_remain_redacted_to_allowlist` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-032` | `posts` | passing | `test_v2_input_does_not_reach_raw_sql_and_routes_use_parameter_binding` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-033` | `frontend` | passing | `test_v2_agent_authored_content_renders_as_plain_text_with_no_html_injection` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-034` | `frontend` | passing | `test_v2_no_markdown_template_or_code_eval_on_agent_authored_content` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-035` | `frontend` | passing | `test_v2_no_external_fetch_on_user_supplied_urls` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-036` | `frontend` | passing | `test_v2_cache_and_content_type_headers_match_spec_requirements` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
| `V2-RT-037` | `frontend` | passing | `test_v2_cors_disabled_by_default_or_allowlisted_only_for_local_reads` | Covered by scenario runner batch checks; no raw traces or credentials recorded. |
