from beyo_manager.sockets.manager import manager


async def handle_push_user_signal(payload: dict) -> None:
    user_id = payload.get("user_id")
    signal  = payload.get("signal")
    if user_id and signal:
        await manager.send_to_user(user_id, "user:signal", {"signal": signal})
