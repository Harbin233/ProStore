from aiogram import Router, types

router = Router()

@router.message()
async def catch_all_messages(message: types.Message):
    print(f"\n[AIROGRAM] НЕОБРАБОТАННОЕ СООБЩЕНИЕ:\n{message.model_dump_json(indent=2)}\n")

@router.callback_query()
async def catch_all_callbacks(callback: types.CallbackQuery):
    print(f"\n[AIROGRAM] НЕОБРАБОТАННЫЙ CALLBACK:\n{callback.model_dump_json(indent=2)}\n")