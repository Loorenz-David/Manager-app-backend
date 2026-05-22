# Database Tables Overview

## Summary

- [audit_logs](#audit-logs)
- [case_conversation_messages](#case-conversation-messages)
- [case_conversations](#case-conversations)
- [case_links](#case-links)
- [case_participants](#case-participants)
- [case_types](#case-types)
- [cases](#cases)
- [content_mention_links](#content-mention-links)
- [content_mentions](#content-mentions)
- [customers](#customers)
- [delayed_schedulers](#delayed-schedulers)
- [execution_payloads](#execution-payloads)
- [execution_tasks](#execution-tasks)
- [history_record_links](#history-record-links)
- [history_records](#history-records)
- [image_annotations](#image-annotations)
- [image_events](#image-events)
- [image_links](#image-links)
- [images](#images)
- [issue_category_configs](#issue-category-configs)
- [issue_severities](#issue-severities)
- [issue_types](#issue-types)
- [item_categories](#item-categories)
- [item_issues](#item-issues)
- [item_upholsteries](#item-upholsteries)
- [item_upholstery_requirements](#item-upholstery-requirements)
- [items](#items)
- [notification_pins](#notification-pins)
- [notifications](#notifications)
- [pending_uploads](#pending-uploads)
- [push_subscriptions](#push-subscriptions)
- [recurring_schedulers](#recurring-schedulers)
- [roles](#roles)
- [static_costs](#static-costs)
- [step_state_records](#step-state-records)
- [task_events](#task-events)
- [task_items](#task-items)
- [task_notes](#task-notes)
- [task_step_assignment_records](#task-step-assignment-records)
- [task_step_dependencies](#task-step-dependencies)
- [task_steps](#task-steps)
- [tasks](#tasks)
- [upholsteries](#upholsteries)
- [upholstery_inventory](#upholstery-inventory)
- [user_app_view_records](#user-app-view-records)
- [user_daily_work_stats](#user-daily-work-stats)
- [user_history_records](#user-history-records)
- [user_lifetime_stats](#user-lifetime-stats)
- [user_section_daily_work_stats](#user-section-daily-work-stats)
- [user_shift_state_records](#user-shift-state-records)
- [user_work_profiles](#user-work-profiles)
- [users](#users)
- [working_section_daily_work_stats](#working-section-daily-work-stats)
- [working_section_dependencies](#working-section-dependencies)
- [working_section_item_categories](#working-section-item-categories)
- [working_section_memberships](#working-section-memberships)
- [working_section_supported_issue_types](#working-section-supported-issue-types)
- [working_sections](#working-sections)
- [workspace_memberships](#workspace-memberships)
- [workspace_roles](#workspace-roles)
- [workspaces](#workspaces)

## audit_logs

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| event | `str` | `String(128)` |
| actor_user_id | `str | None` | `String(64)` |
| actor_label | `str | None` | `String(255)` |
| workspace_id | `str` | `String(64)` |
| resource_type | `str | None` | `String(64)` |
| resource_client_id | `str | None` | `String(64)` |
| detail | `dict` | `JSON` |
| ip_address | `str | None` | `String(64)` |
| user_agent | `str | None` | `String(512)` |
| request_id | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## case_conversation_messages

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| case_conversation_id | `str` | `String(64)` |
| message_seq | `int` | `Integer` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| content | `list | dict` | `JSONB` |
| plain_text | `str` | `Text` |
| has_been_edited | `bool` | `Boolean` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| has_been_deleted | `bool` | `Boolean` |

## case_conversations

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| case_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| state | `CaseStateEnum` | `SAEnum(CaseStateEnum, name='case_state_enum', create_type=False)` |
| last_message_seq | `int` | `Integer` |
| messages_count | `int` | `Integer` |

## case_links

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| case_id | `str` | `String(64)` |
| entity_type | `CaseLinkEntityTypeEnum` | `SAEnum(CaseLinkEntityTypeEnum, name='case_link_entity_type_enum', create_type=False)` |
| entity_client_id | `str` | `String(64)` |
| role | `CaseLinkRoleEnum` | `SAEnum(CaseLinkRoleEnum, name='case_link_role_enum', create_type=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## case_participants

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| case_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| last_read_message_seq | `int` | `Integer` |
| joined_at | `datetime` | `DateTime(timezone=True)` |

## case_types

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| name | `str` | `String(128)` |
| image | `str | None` | `String(512)` |
| description | `str | None` | `String(1024)` |
| entity_type | `CaseLinkEntityTypeEnum` | `SAEnum(CaseLinkEntityTypeEnum, name='case_link_entity_type_enum', create_type=True)` |

## cases

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| state | `CaseStateEnum` | `SAEnum(CaseStateEnum, name='case_state_enum', create_type=True)` |
| case_type_id | `str | None` | `String(64)` |
| type_label | `str | None` | `String(128)` |
| participants_count | `int` | `Integer` |
| conversations_count | `int` | `Integer` |
| messages_count | `int` | `Integer` |

## content_mention_links

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| content_mention_id | `str` | `String(64)` |
| entity_type | `ContentMentionLinkEntityTypeEnum` | `SAEnum(ContentMentionLinkEntityTypeEnum, name='content_mention_link_entity_type_enum', create_type=True)` |
| entity_client_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## content_mentions

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| mention_table | `str` | `String(128)` |
| mention_id | `str` | `String(128)` |

## customers

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| display_name | `str` | `String(255)` |
| customer_type | `CustomerTypeEnum` | `SAEnum(CustomerTypeEnum, name='customer_type_enum', create_type=True)` |
| status | `CustomerStatusEnum` | `SAEnum(CustomerStatusEnum, name='customer_status_enum', create_type=True)` |
| primary_phone_number | `str | None` | `String(64)` |
| primary_email | `str | None` | `String(255)` |
| primary_phone_number_normalized | `str | None` | `String(64)` |
| primary_email_normalized | `str | None` | `String(255)` |
| address | `dict | None` | `JSON` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## delayed_schedulers

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| type | `DelayedSchedulerTypeEnum` | `SAEnum(DelayedSchedulerTypeEnum, name='delayed_scheduler_type_enum', create_type=True)` |
| state | `SchedulerStateEnum` | `SAEnum(SchedulerStateEnum, name='scheduler_state_enum', create_type=True)` |
| origin_source | `SchedulerOriginSourceEnum` | `SAEnum(SchedulerOriginSourceEnum, name='scheduler_origin_source_enum', create_type=True)` |
| origin_id | `str | None` | `String(64)` |
| event_client_id | `str | None` | `String(64)` |
| scheduled_for | `datetime` | `DateTime(timezone=True)` |
| payload_snapshot | `dict` | `JSON` |
| last_error | `str | None` | `String(1024)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| fired_at | `datetime | None` | `DateTime(timezone=True)` |

## execution_payloads

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| origin_source | `EventTaskOriginSourceEnum` | `SAEnum(EventTaskOriginSourceEnum, name='event_task_origin_source_enum', create_type=True)` |
| origin_id | `str | None` | `String(64)` |
| event_client_id | `str | None` | `String(64)` |
| payload | `dict` | `JSON` |
| execution_task_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## execution_tasks

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| task_type | `TaskType` | `SAEnum(TaskType, name='task_type_enum', create_type=True)` |
| state | `ExecutionTaskStateEnum` | `SAEnum(ExecutionTaskStateEnum, name='execution_task_state_enum', create_type=True)` |
| try_count | `int` | `Integer` |
| max_try | `int` | `Integer` |
| last_error | `str | None` | `String(1024)` |
| worker_id | `str | None` | `String(128)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| scheduled_at | `datetime | None` | `DateTime(timezone=True)` |
| started_at | `datetime | None` | `DateTime(timezone=True)` |
| completed_at | `datetime | None` | `DateTime(timezone=True)` |
| locked_at | `datetime | None` | `DateTime(timezone=True)` |
| next_retry_at | `datetime | None` | `DateTime(timezone=True)` |

## history_record_links

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| history_record_id | `str` | `String(64)` |
| entity_type | `HistoryRecordEntityTypeEnum` | `SAEnum(HistoryRecordEntityTypeEnum, name='history_record_entity_type_enum', create_type=False)` |
| entity_client_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## history_records

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| change_type | `HistoryRecordChangeTypeEnum` | `SAEnum(HistoryRecordChangeTypeEnum, name='history_record_change_type_enum', create_type=False)` |
| description | `str | None` | `String(512)` |
| field_name | `str | None` | `String(128)` |
| from_value | `dict | None` | `JSONB` |
| to_value | `dict | None` | `JSONB` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| username_snapshot | `str | None` | `String(128)` |

## image_annotations

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| image_id | `str` | `String(64)` |
| annotation_type | `ImageAnnotationTypeEnum` | `SAEnum(ImageAnnotationTypeEnum, name='image_annotation_type_enum', create_type=True)` |
| data | `dict | None` | `JSONB` |
| accuracy | `int | None` | `Integer` |
| created_by_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## image_events

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| image_id | `str` | `String(64)` |

## image_links

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| image_id | `str` | `String(64)` |
| entity_type | `ImageLinkEntityTypeEnum` | `SAEnum(ImageLinkEntityTypeEnum, name='image_link_entity_type_enum', create_type=True)` |
| entity_client_id | `str` | `String(64)` |
| display_order | `int` | `Integer` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## images

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| image_url | `str` | `String(2048)` |
| storage_provider | `ImageStorageProviderEnum` | `SAEnum(ImageStorageProviderEnum, name='image_storage_provider_enum', create_type=True)` |
| source_type | `ImageSourceTypeEnum` | `SAEnum(ImageSourceTypeEnum, name='image_source_type_enum', create_type=True)` |
| source_reference | `ImageSourceReferenceEnum | None` | `SAEnum(ImageSourceReferenceEnum, name='image_source_reference_enum', create_type=True)` |
| width_px | `int | None` | `Integer` |
| height_px | `int | None` | `Integer` |
| file_size_bytes | `int | None` | `BigInteger` |
| created_by_id | `str` | `String(64)` |
| updated_by_id | `str | None` | `String(64)` |
| deleted_by_id | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| last_event_id | `str | None` | `String(64)` |

## issue_category_configs

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| issue_type_id | `str` | `String(64)` |
| item_category_id | `str` | `String(64)` |
| base_time_seconds | `int` | `Integer` |
| effective_from | `datetime | None` | `DateTime(timezone=True)` |
| effective_to | `datetime | None` | `DateTime(timezone=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## issue_severities

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| name | `str` | `String(128)` |
| time_multiplier | `Decimal` | `Numeric(8, 4)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## issue_types

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| name | `str` | `String(255)` |
| source | `IssueSourceEnum` | `SAEnum(IssueSourceEnum, name='issue_source_enum', create_type=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## item_categories

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| name | `str` | `String(255)` |
| major_category | `ItemMajorCategoryEnum` | `SAEnum(ItemMajorCategoryEnum, name='item_major_category_enum', create_type=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## item_issues

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| item_id | `str` | `String(64)` |
| issue_type_id | `str | None` | `String(64)` |
| issue_severity_id | `str | None` | `String(64)` |
| state | `ItemIssueStateEnum` | `SAEnum(ItemIssueStateEnum, name='item_issue_state_enum', create_type=True)` |
| base_time_seconds | `int | None` | `Integer` |
| time_multiplier | `Decimal | None` | `Numeric(8, 4)` |
| issue_name_snapshot | `str | None` | `String(255)` |
| severity_name_snapshot | `str | None` | `String(255)` |
| created_by_id | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| started_at | `datetime | None` | `DateTime(timezone=True)` |
| resolved_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## item_upholsteries

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| item_id | `str` | `String(64)` |
| upholstery_id | `str | None` | `String(64)` |
| name | `str | None` | `String(255)` |
| code | `str | None` | `String(128)` |
| amount_meters | `Decimal | None` | `Numeric(12, 3)` |
| source | `ItemUpholsterySourceEnum` | `SAEnum(ItemUpholsterySourceEnum, name='item_upholstery_source_enum', create_type=True)` |
| time_to_fix_in_seconds | `int | None` | `Integer` |
| active_requirement_id | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## item_upholstery_requirements

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| item_upholstery_id | `str` | `String(64)` |
| upholstery_inventory_id | `str | None` | `String(64)` |
| amount_meters | `Decimal | None` | `Numeric(12, 3)` |
| value_minor | `int | None` | `Integer` |
| currency | `ItemCurrencyEnum | None` | `SAEnum(ItemCurrencyEnum, name='item_currency_enum', create_type=False)` |
| source | `ItemUpholsteryRequirementSourceEnum` | `SAEnum(ItemUpholsteryRequirementSourceEnum, name='item_upholstery_requirement_source_enum', create_type=True)` |
| state | `ItemUpholsteryRequirementStateEnum` | `SAEnum(ItemUpholsteryRequirementStateEnum, name='item_upholstery_requirement_state_enum', create_type=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| ordered_at | `datetime | None` | `DateTime(timezone=True)` |
| in_use_at | `datetime | None` | `DateTime(timezone=True)` |
| completed_at | `datetime | None` | `DateTime(timezone=True)` |
| failed_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## items

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| article_number | `str | None` | `String(128)` |
| sku | `str | None` | `String(128)` |
| state | `ItemStateEnum` | `SAEnum(ItemStateEnum, name='item_state_enum', create_type=True)` |
| item_category_id | `str | None` | `String(64)` |
| quantity | `int` | `Integer` |
| designer | `str | None` | `String(255)` |
| height_in_cm | `int | None` | `Integer` |
| width_in_cm | `int | None` | `Integer` |
| depth_in_cm | `int | None` | `Integer` |
| item_value_minor | `int | None` | `Integer` |
| item_cost_minor | `int | None` | `Integer` |
| item_currency | `ItemCurrencyEnum | None` | `SAEnum(ItemCurrencyEnum, name='item_currency_enum', create_type=True)` |
| item_position | `str | None` | `String(255)` |
| external_id | `str | None` | `String(255)` |
| external_url | `str | None` | `String(1024)` |
| external_source | `str | None` | `String(128)` |
| external_order_id | `str | None` | `String(255)` |
| item_category_snapshot | `str | None` | `String(255)` |
| item_major_category_snapshot | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## notification_pins

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| entity_type | `str` | `String(64)` |
| entity_client_id | `str` | `String(128)` |
| pinned_at | `datetime` | `DateTime(timezone=True)` |

## notifications

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| notification_type | `str` | `String(64)` |
| title | `str` | `String(256)` |
| body | `str` | `Text` |
| entity_type | `str | None` | `String(64)` |
| entity_client_id | `str | None` | `String(128)` |
| read_at | `datetime | None` | `DateTime(timezone=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## pending_uploads

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| created_by_id | `str` | `String(64)` |
| storage_key | `str` | `String(512)` |
| file_name | `str` | `String(255)` |
| content_type | `str` | `String(128)` |
| status | `PendingUploadStatusEnum` | `SAEnum(PendingUploadStatusEnum, name='pending_upload_status_enum', create_type=True)` |
| expires_at | `datetime` | `DateTime(timezone=True)` |
| size_bytes | `int | None` | `BigInteger` |
| upload_id | `str | None` | `String(256)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## push_subscriptions

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| endpoint | `str` | `Text` |
| p256dh | `str` | `Text` |
| auth | `str` | `Text` |
| device_label | `str | None` | `String(128)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| last_used_at | `datetime | None` | `DateTime(timezone=True)` |

## recurring_schedulers

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| type | `RecurringSchedulerTypeEnum` | `SAEnum(RecurringSchedulerTypeEnum, name='recurring_scheduler_type_enum', create_type=True)` |
| state | `SchedulerStateEnum` | `SAEnum(SchedulerStateEnum, name='scheduler_state_enum', create_type=True)` |
| origin_source | `SchedulerOriginSourceEnum` | `SAEnum(SchedulerOriginSourceEnum, name='scheduler_origin_source_enum', create_type=True)` |
| origin_id | `str | None` | `String(64)` |
| event_client_id | `str | None` | `String(64)` |
| interval | `int` | `Integer` |
| interval_value | `RecurringSchedulerIntervalValueEnum` | `SAEnum(RecurringSchedulerIntervalValueEnum, name='recurring_scheduler_interval_value_enum', create_type=True)` |
| last_interval | `datetime | None` | `DateTime(timezone=True)` |
| payload_snapshot | `dict` | `JSON` |
| last_error | `str | None` | `String(1024)` |
| created_at | `datetime` | `DateTime(timezone=True)` |

## roles

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| name | `RoleNameEnum` | `SAEnum(RoleNameEnum, name='role_name_enum', create_type=True)` |

## static_costs

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| name | `str` | `String(255)` |
| description | `str | None` | `String(1024)` |
| cost_minor | `int` | `Integer` |
| currency | `StaticCostCurrencyEnum` | `SAEnum(StaticCostCurrencyEnum, name='static_cost_currency_enum', create_type=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## step_state_records

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| step_id | `str` | `String(64)` |
| state | `TaskStepStateEnum` | `SAEnum(TaskStepStateEnum, name='task_step_state_enum', create_type=False)` |
| reason | `StepEventReasonEnum | None` | `SAEnum(StepEventReasonEnum, name='step_event_reason_enum', create_type=True)` |
| description | `str | None` | `String(1024)` |
| accuracy | `int | None` | `Integer` |
| accuracy_measured_by | `StepStateRecordAccuracyMeasuredByEnum | None` | `SAEnum(StepStateRecordAccuracyMeasuredByEnum, name='step_state_record_accuracy_measured_by_enum', create_type=True)` |
| taken_from_average | `bool` | `Boolean` |
| recorded_time_marked_wrong | `bool` | `Boolean` |
| entered_at | `datetime` | `DateTime(timezone=True)` |
| exited_at | `datetime | None` | `DateTime(timezone=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## task_events

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| task_id | `str` | `String(64)` |
| event_type | `TaskEventTypeEnum` | `SAEnum(TaskEventTypeEnum, name='task_event_type_enum', create_type=True)` |
| event_lifecycle_state | `TaskDomainEventLifecycleStateEnum` | `SAEnum(TaskDomainEventLifecycleStateEnum, name='task_domain_event_lifecycle_state_enum', create_type=True)` |
| error_code | `TaskEventErrorCodeEnum | None` | `SAEnum(TaskEventErrorCodeEnum, name='task_event_error_code_enum', create_type=True)` |
| payload | `dict | None` | `JSON` |
| occurred_at | `datetime` | `DateTime(timezone=True)` |
| correlation_id | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## task_items

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| task_id | `str` | `String(64)` |
| item_id | `str` | `String(64)` |
| role | `TaskItemRoleEnum` | `SAEnum(TaskItemRoleEnum, name='task_item_role_enum', create_type=True)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| removed_at | `datetime | None` | `DateTime(timezone=True)` |
| removed_by_id | `str | None` | `String(64)` |

## task_notes

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| task_id | `str` | `String(64)` |
| note_type | `TaskNoteTypeEnum` | `SAEnum(TaskNoteTypeEnum, name='task_note_type_enum', create_type=True)` |
| content | `dict` | `JSON` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## task_step_assignment_records

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| step_id | `str` | `String(64)` |
| assigned_worker_id | `str` | `String(64)` |
| assigned_at | `datetime` | `DateTime(timezone=True)` |
| assigned_by_id | `str | None` | `String(64)` |
| removed_at | `datetime | None` | `DateTime(timezone=True)` |
| removed_by_id | `str | None` | `String(64)` |
| reason_code | `str | None` | `String(128)` |
| reason_text | `str | None` | `String(512)` |

## task_step_dependencies

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| dependent_step_id | `str` | `String(64)` |
| prerequisite_step_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| removed_at | `datetime | None` | `DateTime(timezone=True)` |
| removed_by_id | `str | None` | `String(64)` |

## task_steps

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| task_id | `str` | `String(64)` |
| state | `TaskStepStateEnum` | `SAEnum(TaskStepStateEnum, name='task_step_state_enum', create_type=True)` |
| readiness_status | `TaskStepReadinessStatusEnum` | `SAEnum(TaskStepReadinessStatusEnum, name='task_step_readiness_status_enum', create_type=True)` |
| sequence_order | `int | None` | `Integer` |
| working_section_id | `str` | `String(64)` |
| assigned_worker_id | `str | None` | `String(64)` |
| total_dependencies | `int` | `Integer` |
| completed_dependencies | `int` | `Integer` |
| recorded_time_marked_wrong | `bool` | `Boolean` |
| taken_from_average | `bool` | `Boolean` |
| working_section_name_snapshot | `str | None` | `String(255)` |
| assigned_worker_display_name_snapshot | `str | None` | `String(255)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| closed_at | `datetime | None` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| latest_state_record_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## tasks

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| task_scalar_id | `int` | `Integer` |
| task_type | `TaskTypeEnum` | `SAEnum(TaskTypeEnum, name='business_task_type_enum', create_type=True)` |
| priority | `TaskPriorityEnum` | `SAEnum(TaskPriorityEnum, name='task_priority_enum', create_type=True)` |
| state | `TaskStateEnum` | `SAEnum(TaskStateEnum, name='task_state_enum', create_type=True)` |
| title | `str | None` | `String(255)` |
| summary | `str | None` | `String(1024)` |
| return_source | `TaskReturnSourceEnum | None` | `SAEnum(TaskReturnSourceEnum, name='task_return_source_enum', create_type=True)` |
| item_location | `TaskItemLocationEnum | None` | `SAEnum(TaskItemLocationEnum, name='task_item_location_enum', create_type=True)` |
| additional_details | `dict | None` | `JSON` |
| ready_by_at | `datetime | None` | `DateTime(timezone=True)` |
| scheduled_start_at | `datetime | None` | `DateTime(timezone=True)` |
| scheduled_end_at | `datetime | None` | `DateTime(timezone=True)` |
| return_method | `TaskReturnMethodEnum | None` | `SAEnum(TaskReturnMethodEnum, name='task_return_method_enum', create_type=True)` |
| fulfillment_method | `TaskFulfillmentMethodEnum | None` | `SAEnum(TaskFulfillmentMethodEnum, name='task_fulfillment_method_enum', create_type=True)` |
| customer_id | `str | None` | `String(64)` |
| primary_phone_number | `str | None` | `String(64)` |
| secondary_phone_number | `str | None` | `String(64)` |
| primary_email | `str | None` | `String(255)` |
| secondary_email | `str | None` | `String(255)` |
| address | `dict | None` | `JSON` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| closed_at | `datetime | None` | `DateTime(timezone=True)` |
| latest_event_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |
| recorded_time_marked_wrong | `bool` | `Boolean` |
| taken_from_average | `bool` | `Boolean` |

## upholsteries

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| name | `str` | `String(255)` |
| code | `str | None` | `String(128)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## upholstery_inventory

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| upholstery_id | `str` | `String(64)` |
| minimum_to_have | `int | None` | `Integer` |
| maximum_to_have | `int | None` | `Integer` |
| projected_inventory_value_minor | `int | None` | `Integer` |
| currency | `UpholsteryCurrencyEnum | None` | `SAEnum(UpholsteryCurrencyEnum, name='upholstery_currency_enum', create_type=True)` |
| planning_position | `str | None` | `String(255)` |
| inventory_condition | `UpholsteryInventoryConditionEnum` | `SAEnum(UpholsteryInventoryConditionEnum, name='upholstery_inventory_condition_enum', create_type=True)` |
| current_stored_amount_meters | `Decimal | None` | `Numeric(14, 3)` |
| current_amount_in_use_meters | `Decimal | None` | `Numeric(14, 3)` |
| current_amount_in_need_meters | `Decimal | None` | `Numeric(14, 3)` |
| current_amount_ordered_meters | `Decimal | None` | `Numeric(14, 3)` |
| total_upholstery_used_meters | `Decimal | None` | `Numeric(14, 3)` |
| total_upholstery_used_inventory_meters | `Decimal | None` | `Numeric(14, 3)` |
| total_upholstery_used_surplus_meters | `Decimal | None` | `Numeric(14, 3)` |
| total_upholstery_surplus_meters | `Decimal | None` | `Numeric(14, 3)` |
| low_stock_threshold_meters | `Decimal | None` | `Numeric(14, 3)` |
| latest_projection_history_id | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## user_app_view_records

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| entity_type | `str` | `String(128)` |
| entity_client_id | `str | None` | `String(128)` |
| started_at | `datetime` | `DateTime(timezone=True)` |
| ended_at | `datetime | None` | `DateTime(timezone=True)` |

## user_daily_work_stats

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| user_display_name_snapshot | `str` | `String(255)` |
| work_date | `date` | `Date` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| updated_at | `datetime` | `DateTime(timezone=True)` |

## user_history_records

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |

## user_lifetime_stats

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| user_display_name_snapshot | `str` | `String(255)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| updated_at | `datetime` | `DateTime(timezone=True)` |

## user_section_daily_work_stats

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| working_section_id | `str` | `String(64)` |
| section_name_snapshot | `str` | `String(255)` |
| user_display_name_snapshot | `str` | `String(255)` |
| work_date | `date` | `Date` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| updated_at | `datetime` | `DateTime(timezone=True)` |

## user_shift_state_records

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| state | `UserShiftStateEnum` | `SAEnum(UserShiftStateEnum, name='user_shift_state_enum', create_type=True)` |
| entered_at | `datetime` | `DateTime(timezone=True)` |
| exited_at | `datetime | None` | `DateTime(timezone=True)` |
| changed_by_id | `str | None` | `String(64)` |

## user_work_profiles

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| salary_per_hour_before_tax | `Decimal | None` | `Numeric(12, 4)` |
| salary_per_hour_after_tax | `Decimal | None` | `Numeric(12, 4)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| created_by_id | `str` | `String(64)` |
| updated_by_id | `str | None` | `String(64)` |

## users

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| username | `str` | `String(128)` |
| phone_number | `str | None` | `String(32)` |
| email | `str` | `String(255)` |
| password | `str` | `String(255)` |
| languages | `str | None` | `String(512)` |
| language_preference | `str | None` | `String(16)` |
| profile_picture | `str | None` | `String(512)` |
| online | `bool` | `Boolean` |
| last_online | `datetime | None` | `DateTime(timezone=True)` |
| last_app_view_record_id | `str | None` | `String(64)` |
| last_history_record_id | `str | None` | `String(64)` |

## working_section_daily_work_stats

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| working_section_id | `str` | `String(64)` |
| section_name_snapshot | `str` | `String(255)` |
| work_date | `date` | `Date` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| updated_at | `datetime` | `DateTime(timezone=True)` |

## working_section_dependencies

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| dependent_section_id | `str` | `String(64)` |
| prerequisite_section_id | `str` | `String(64)` |

## working_section_item_categories

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| working_section_id | `str` | `String(64)` |
| item_category_id | `str` | `String(64)` |

## working_section_memberships

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| working_section_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| assigned_at | `datetime` | `DateTime(timezone=True)` |
| assigned_by_id | `str` | `String(64)` |
| removed_at | `datetime | None` | `DateTime(timezone=True)` |
| removed_by_id | `str | None` | `String(64)` |

## working_section_supported_issue_types

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| working_section_id | `str` | `String(64)` |
| issue_type_id | `str` | `String(64)` |

## working_sections

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| name | `str` | `String(255)` |
| image | `str | None` | `String(512)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
| created_by_id | `str | None` | `String(64)` |
| updated_at | `datetime | None` | `DateTime(timezone=True)` |
| updated_by_id | `str | None` | `String(64)` |
| is_deleted | `bool` | `Boolean` |
| deleted_at | `datetime | None` | `DateTime(timezone=True)` |
| deleted_by_id | `str | None` | `String(64)` |

## workspace_memberships

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| user_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| workspace_role_id | `str` | `String(64)` |
| is_active | `bool` | `Boolean` |
| joined_at | `datetime` | `DateTime(timezone=True)` |

## workspace_roles

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| workspace_id | `str` | `String(64)` |
| role_id | `str` | `String(64)` |
| name | `str` | `String(64)` |
| description | `str | None` | `String(255)` |
| is_system | `bool` | `Boolean` |

## workspaces

| Column | Mapped Type | SQLAlchemy Type |
| :--- | :--- | :--- |
| client_id | `str` | `String(64)` |
| name | `str` | `String(255)` |
| time_zone | `str` | `String(64)` |
| created_by_id | `str | None` | `String(64)` |
| created_at | `datetime` | `DateTime(timezone=True)` |
