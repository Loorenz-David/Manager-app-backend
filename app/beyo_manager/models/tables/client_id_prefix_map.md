# Client ID Prefix Map

This document lists all `CLIENT_ID_PREFIX` abbreviations used for client_id generation in the backend tables. The frontend should use these prefixes when generating client IDs for new instances.

| Table/Class | CLIENT_ID_PREFIX | Example client_id |
|-------------|------------------|-------------------|
| AuditLog | aud | aud_xxxxxxx |
| Case | ca | ca_xxxxxxx |
| CaseConversation | ccv | ccv_xxxxxxx |
| CaseConversationMessage | ccm | ccm_xxxxxxx |
| CaseLink | clk | clk_xxxxxxx |
| CaseParticipant | cpa | cpa_xxxxxxx |
| CaseType | cty | cty_xxxxxxx |
| ContentMention | cmt | cmt_xxxxxxx |
| ContentMentionLink | cml | cml_xxxxxxx |
| Customer | cus | cus_xxxxxxx |
| ExecutionPayload | epl | epl_xxxxxxx |
| ExecutionTask | task | task_xxxxxxx |
| HistoryRecord | hrec | hrec_xxxxxxx |
| HistoryRecordLink | hrlk | hrlk_xxxxxxx |
| Image | img | img_xxxxxxx |
| ImageAnnotation | ian | ian_xxxxxxx |
| ImageEvent | iev | iev_xxxxxxx |
| ImageLink | iml | iml_xxxxxxx |
| Item | itm | itm_xxxxxxx |
| ItemCategory | itc | itc_xxxxxxx |
| ItemIssue | iis | iis_xxxxxxx |
| ItemUpholstery | iup | iup_xxxxxxx |
| ItemUpholsteryRequirement | iur | iur_xxxxxxx |
| Notification | not | not_xxxxxxx |
| NotificationPin | npn | npn_xxxxxxx |
| PendingUpload | upl | upl_xxxxxxx |
| PushSubscription | psu | psu_xxxxxxx |
| RecurringScheduler | rsch | rsch_xxxxxxx |
| Role | role | role_xxxxxxx |
| StaticCost | stc | stc_xxxxxxx |
| StepStateRecord | ssr | ssr_xxxxxxx |
| TaskEvent | tev | tev_xxxxxxx |
| TaskItem | tki | tki_xxxxxxx |
| TaskNote | tno | tno_xxxxxxx |
| TaskStep | tsp | tsp_xxxxxxx |
| TaskStepAssignmentRecord | tsar | tsar_xxxxxxx |
| TaskStepDependency | tsd | tsd_xxxxxxx |
| Upholstery | uph | uph_xxxxxxx |
| UpholsteryInventory | uphi | uphi_xxxxxxx |
| User | usr | usr_xxxxxxx |
| UserAppViewRecord | uavr | uavr_xxxxxxx |
| UserDailyWorkStats | udwr | udwr_xxxxxxx |
| UserHistoryRecord | uhr | uhr_xxxxxxx |
| UserLifetimeStats | usr_stat | usr_stat_xxxxxxx |
| UserSectionDailyWorkStats | usdwr | usdwr_xxxxxxx |
| UserShiftStateRecord | ussr | ussr_xxxxxxx |
| UserWorkProfile | uwp | uwp_xxxxxxx |
| Workspace | ws | ws_xxxxxxx |
| WorkspaceMembership | wsm | wsm_xxxxxxx |
| WorkspaceRole | wsr | wsr_xxxxxxx |
| WorkingSection | wks | wks_xxxxxxx |
| WorkingSectionDependency | wsd | wsd_xxxxxxx |
| WorkingSectionItemCategory | wsic | wsic_xxxxxxx |
| WorkingSectionMembership | wsmem | wsmem_xxxxxxx |
| WorkingSectionSupportedIssueType | wssit | wssit_xxxxxxx |
| WorkingSectionDailyWorkStats | wsdws | wsdws_xxxxxxx |

> **Note:** This map is auto-generated from the codebase. If you add a new table with a client_id, ensure to update this document accordingly.
