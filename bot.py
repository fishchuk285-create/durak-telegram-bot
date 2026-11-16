import os
import asyncio
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from game_logic import DurakGame

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

games: dict[str, DurakGame] = {}
user_room: dict[int, str] = {}


def format_card(card):
    return f"{card[0]}{card[1]}"


def build_game_view(game: DurakGame, viewer_id: int):
    opponent_id = [pid for pid in game.player_ids if pid != viewer_id][0]
    opponent = game.players[opponent_id]
    viewer = game.players[viewer_id]

    if game.winner:
        text = f"🏆 **Гра закінчена!**\nПереможець: **{game.winner}**\n\nНатисни /newgame щоб зіграти ще."
        return text, None

    table_str = "Стіл порожній"
    if game.table:
        pairs = []
        for a, d in game.table:
            if d:
                pairs.append(f"{format_card(a)} ➔ {format_card(d)}")
            else:
                pairs.append(f"{format_card(a)} ➔ ❓")
        table_str = "\n".join(pairs)

    status = "⚔️ **Твій хід (Атака)**" if viewer_id == game.attacker_id else "🛡 **Твій захист**"

    text = (
        f"🃏 **Кімната:** `{game.room_id}`\n"
        f"Козир: **{format_card(game.trump_card)}** | В колоді: **{len(game.deck)}**\n"
        f"Суперник ({opponent['name']}): **{len(opponent['hand'])} карт**\n"
        f"───────────────\n"
        f"{table_str}\n"
        f"───────────────\n"
        f"{status}"
    )

    buttons = []
    row = []
    for idx, card in enumerate(viewer["hand"]):
        row.append(InlineKeyboardButton(text=format_card(card), callback_data=f"card:{idx}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    action_row = []
    if viewer_id == game.attacker_id and game.table and all(d is not None for _, d in game.table):
        action_row.append(InlineKeyboardButton(text="✅ Бито", callback_data="act:bito"))
    elif viewer_id == game.defender_id and any(d is None for _, d in game.table):
        action_row.append(InlineKeyboardButton(text="📥 Взяти карти", callback_data="act:take"))

    if action_row:
        buttons.append(action_row)

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


async def update_both_players(game: DurakGame):
    for pid in game.player_ids:
        text, kb = build_game_view(game, pid)
        msg_id = game.players[pid]["msg_id"]
        try:
            if msg_id:
                await bot.edit_message_text(
                    chat_id=pid, message_id=msg_id, text=text, reply_markup=kb, parse_mode="Markdown"
                )
            else:
                msg = await bot.send_message(chat_id=pid, text=text, reply_markup=kb, parse_mode="Markdown")
                game.players[pid]["msg_id"] = msg.message_id
        except Exception as e:
            print(f"Помилка оновлення для {pid}: {e}")


@dp.message(Command("newgame"))
async def cmd_newgame(message: Message):
    room_id = f"room_{random.randint(1000, 9999)}"
    game = DurakGame(room_id, message.from_user.id, message.from_user.first_name)
    games[room_id] = game
    user_room[message.from_user.id] = room_id

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={room_id}"

    await message.answer(
        f"🎮 **Кімнату створено!**\n\n"
        f"Перешли це посилання другу, щоб почати гру:\n`{invite_link}`",
        parse_mode="Markdown"
    )


@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    args = command.args
    if args and args in games:
        game = games[args]
        if game.is_started:
            await message.answer("❌ Ця кімната вже заповнена.")
            return

        if game.add_player(message.from_user.id, message.from_user.first_name):
            user_room[message.from_user.id] = args
            await update_both_players(game)
        else:
            await message.answer("❌ Не вдалося приєднатися до гри.")
    else:
        await message.answer("Привіт! Натисни /newgame, щоб створити гру в «Дурака» для двох.")


@dp.callback_query(F.data.startswith("card:"))
async def on_card_click(callback: CallbackQuery):
    uid = callback.from_user.id
    room_id = user_room.get(uid)
    if not room_id or room_id not in games:
        await callback.answer("Гра не знайдена", show_alert=True)
        return

    game = games[room_id]
    card_idx = int(callback.data.split(":")[1])
    success, msg = game.make_move(uid, card_idx)

    if not success:
        await callback.answer(msg, show_alert=True)
    else:
        await callback.answer()
        await update_both_players(game)


@dp.callback_query(F.data.startswith("act:"))
async def on_action_click(callback: CallbackQuery):
    uid = callback.from_user.id
    room_id = user_room.get(uid)
    if not room_id or room_id not in games:
        return

    game = games[room_id]
    action = callback.data.split(":")[1]

    if action == "bito":
        success, msg = game.action_bito(uid)
    else:
        success, msg = game.action_take(uid)

    if not success:
        await callback.answer(msg, show_alert=True)
    else:
        await callback.answer(msg)
        await update_both_players(game)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())