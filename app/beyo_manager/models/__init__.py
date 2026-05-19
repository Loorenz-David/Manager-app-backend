from beyo_manager.models.base.base import Base  # noqa: F401

# Import every table module here so Alembic detects schema changes.
# Add one line per domain as you build it:
# from beyo_manager.models.tables.users import user  # noqa: F401
from beyo_manager.models.tables.users import user  # noqa: F401
from beyo_manager.models.tables.users import user_app_view_record  # noqa: F401
from beyo_manager.models.tables.users import user_history_record  # noqa: F401
from beyo_manager.models.tables.roles import role  # noqa: F401
from beyo_manager.models.tables.roles import workspace_role  # noqa: F401
from beyo_manager.models.tables.workspaces import workspace  # noqa: F401
from beyo_manager.models.tables.workspaces import workspace_membership  # noqa: F401
from beyo_manager.models.tables.execution import execution_task  # noqa: F401
from beyo_manager.models.tables.execution import execution_payload  # noqa: F401
from beyo_manager.models.tables.audit import audit_log  # noqa: F401
from beyo_manager.models.tables.notifications import notification  # noqa: F401
from beyo_manager.models.tables.notifications import notification_pin  # noqa: F401
from beyo_manager.models.tables.notifications import push_subscription  # noqa: F401
from beyo_manager.models.tables.files import pending_upload  # noqa: F401
from beyo_manager.models.tables.content import content_mention  # noqa: F401
from beyo_manager.models.tables.content import content_mention_link  # noqa: F401
from beyo_manager.models.tables.cases import case  # noqa: F401
from beyo_manager.models.tables.cases import case_conversation  # noqa: F401
from beyo_manager.models.tables.cases import case_conversation_message  # noqa: F401
from beyo_manager.models.tables.cases import case_link  # noqa: F401
from beyo_manager.models.tables.cases import case_participant  # noqa: F401
from beyo_manager.models.tables.cases import case_type  # noqa: F401
from beyo_manager.models.tables.images import image  # noqa: F401
from beyo_manager.models.tables.images import image_annotation  # noqa: F401
from beyo_manager.models.tables.images import image_event  # noqa: F401
from beyo_manager.models.tables.images import image_link  # noqa: F401

# --- History records ---
from beyo_manager.models.tables.history import history_record  # noqa: F401
from beyo_manager.models.tables.history import history_record_link  # noqa: F401

from beyo_manager.models.tables.schedulers import delayed_scheduler  # noqa: F401
from beyo_manager.models.tables.schedulers import recurring_scheduler  # noqa: F401

# --- User domain extensions ---
from beyo_manager.models.tables.users import user_work_profile  # noqa: F401
from beyo_manager.models.tables.users import user_shift_state_record  # noqa: F401

# --- Working sections ---
from beyo_manager.models.tables.working_sections import working_section  # noqa: F401
from beyo_manager.models.tables.working_sections import working_section_membership  # noqa: F401
from beyo_manager.models.tables.working_sections import working_section_dependency  # noqa: F401

# --- Issue type registry ---
from beyo_manager.models.tables.issue_types import issue_type  # noqa: F401
from beyo_manager.models.tables.issue_types import issue_severity  # noqa: F401

# --- Item categories (before working section bridges and items) ---
from beyo_manager.models.tables.items import item_category  # noqa: F401

# --- Working section bridge tables (depend on item_category and issue_type) ---
from beyo_manager.models.tables.working_sections import working_section_item_category  # noqa: F401
from beyo_manager.models.tables.working_sections import working_section_supported_issue_type  # noqa: F401

# --- Issue category config (depends on issue_type and item_category) ---
from beyo_manager.models.tables.issue_types import issue_category_config  # noqa: F401

# --- Upholstery registry ---
from beyo_manager.models.tables.upholstery import upholstery  # noqa: F401

# --- Items (depends on item_category) ---
from beyo_manager.models.tables.items import item  # noqa: F401

# --- Item issues (depends on item, issue_type, issue_severity) ---
from beyo_manager.models.tables.items import item_issue  # noqa: F401

# --- Item upholstery (depends on item, upholstery; use_alter FK to item_upholstery_requirement) ---
from beyo_manager.models.tables.items import item_upholstery  # noqa: F401

# --- Item upholstery requirements (depends on item_upholstery) ---
from beyo_manager.models.tables.items import item_upholstery_requirement  # noqa: F401

# --- Upholstery inventory (depends on upholstery) ---
from beyo_manager.models.tables.upholstery import upholstery_inventory  # noqa: F401

# --- Customers ---
from beyo_manager.models.tables.customers import customer  # noqa: F401

# --- Static costs ---
from beyo_manager.models.tables.static_costs import static_cost  # noqa: F401

# --- Tasks (depends on customer; use_alter FK to task_event) ---
from beyo_manager.models.tables.tasks import task  # noqa: F401

# --- Task events (depends on task) ---
from beyo_manager.models.tables.tasks import task_event  # noqa: F401

# --- Task notes (depends on task) ---
from beyo_manager.models.tables.tasks import task_note  # noqa: F401

# --- Task items / bridge (depends on task and item) ---
from beyo_manager.models.tables.tasks import task_item  # noqa: F401

# --- Task steps (depends on task, working_section; use_alter FK to step_state_record) ---
from beyo_manager.models.tables.tasks import task_step  # noqa: F401

# --- Step state records (depends on task_step) ---
from beyo_manager.models.tables.tasks import step_state_record  # noqa: F401

# --- Task step dependencies (depends on task_step) ---
from beyo_manager.models.tables.tasks import task_step_dependency  # noqa: F401

# --- Task step assignment records (depends on task_step) ---
from beyo_manager.models.tables.tasks import task_step_assignment_record  # noqa: F401

# --- Analytics aggregates (depends on users and working_sections) ---
from beyo_manager.models.tables.analytics import user_lifetime_stats  # noqa: F401
from beyo_manager.models.tables.analytics import user_daily_work_stats  # noqa: F401
from beyo_manager.models.tables.analytics import user_section_daily_work_stats  # noqa: F401
from beyo_manager.models.tables.analytics import working_section_daily_work_stats  # noqa: F401
