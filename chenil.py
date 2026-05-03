# chenil.py

import os
import time
import psycopg2
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from new_db import get_new_captures, add_xp, evolve_pokemon

SECONDES_PAR_TRANCHE = 120
XP_PAR_TRANCHE       = 50
TICK_MINUTES         = 1

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS chenil (
    user_id         TEXT PRIMARY KEY,
    pokemon_name    TEXT NOT NULL,
    vocal_seconds   INTEGER DEFAULT 0
);
""")
conn.commit()


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_chenil(user_id):
    cur.execute("SELECT pokemon_name, vocal_seconds FROM chenil WHERE user_id = %s", (str(user_id),))
    row = cur.fetchone()
    return {"pokemon_name": row[0], "vocal_seconds": row[1]} if row else None

def set_chenil(user_id, pokemon_name):
    cur.execute("""
        INSERT INTO chenil (user_id, pokemon_name, vocal_seconds)
        VALUES (%s, %s, 0)
        ON CONFLICT (user_id) DO UPDATE
            SET pokemon_name = EXCLUDED.pokemon_name,
                vocal_seconds = 0
    """, (str(user_id), pokemon_name))
    conn.commit()

def remove_chenil(user_id):
    cur.execute("DELETE FROM chenil WHERE user_id = %s", (str(user_id),))
    conn.commit()

def add_vocal_seconds(user_id, seconds):
    entry = get_chenil(user_id)
    if not entry:
        return 0
    new_seconds = entry["vocal_seconds"] + seconds
    full_tranches = new_seconds // SECONDES_PAR_TRANCHE
    remainder     = new_seconds % SECONDES_PAR_TRANCHE
    cur.execute("UPDATE chenil SET vocal_seconds = %s WHERE user_id = %s", (remainder, str(user_id)))
    conn.commit()
    return int(full_tranches)


# ── Cog principal ─────────────────────────────────────────────────────────────

class ChenilCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._vocal_start: dict[int, float] = {}
        self.tick_vocal.start()

    def cog_unload(self):
        self.tick_vocal.cancel()

    # ── Tâche de fond ─────────────────────────────────────────────────────────
    @tasks.loop(minutes=TICK_MINUTES)
    async def tick_vocal(self):
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    entry = get_chenil(member.id)
                    if not entry:
                        continue

                    tranches = add_vocal_seconds(member.id, TICK_MINUTES * 60)
                    if tranches > 0:
                        await self._give_xp(member, entry, tranches)

    @tick_vocal.before_loop
    async def before_tick(self):
        await self.bot.wait_until_ready()

    # ── Événement vocal ───────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        # Entrée en vocal
        if before.channel is None and after.channel is not None:
            self._vocal_start[member.id] = time.time()

        # Sortie du vocal
        elif before.channel is not None and after.channel is None:
            start = self._vocal_start.pop(member.id, None)
            if start is None:
                return
            entry = get_chenil(member.id)
            if not entry:
                return
            elapsed = int(time.time() - start)
            tranches = add_vocal_seconds(member.id, elapsed)
            if tranches > 0:
                await self._give_xp(member, entry, tranches)

    # ── Logique XP / évolution ────────────────────────────────────────────────
    async def _give_xp(self, member, entry, tranches):
        xp_gained = tranches * XP_PAR_TRANCHE
        pokemon = next(
            (p for p in get_new_captures(str(member.id))
             if p["name"].lower() == entry["pokemon_name"].lower()),
            None
        )
        if not pokemon:
            return

        can_evolve = add_xp(str(member.id), pokemon["name"], xp_gained)

        msg = f"🐾 **{pokemon['name']}** au chenil a gagné **+{xp_gained} XP** grâce à ton temps en vocal !"
        if can_evolve:
            result = evolve_pokemon(str(member.id), pokemon)
            if result["success"]:
                msg += f"\n🎉 Il a évolué en **{result['evo_name']}** ! Il a été retiré du chenil automatiquement."
                remove_chenil(member.id)

        try:
            await member.send(msg)
        except discord.Forbidden:
            pass

    # ── Commandes ─────────────────────────────────────────────────────────────
    @commands.command(name="chenil")
    async def chenil_cmd(self, ctx, *, pokemon_name: str = None):
        if pokemon_name is None:
            await ctx.send("❌ Précise le nom du Pokémon.\nUsage : `!chenil <nom_pokemon>`")
            return

        user_id  = str(ctx.author.id)
        captures = get_new_captures(user_id)
        pokemon  = next((p for p in captures if p["name"].lower() == pokemon_name.lower()), None)

        if not pokemon:
            await ctx.send(f"❌ Tu ne possèdes pas de **{pokemon_name}**.")
            return

        existing = get_chenil(user_id)
        if existing:
            await ctx.send(
                f"⚠️ **{existing['pokemon_name']}** est déjà au chenil.\n"
                f"Utilise `!retirer_chenil` pour le récupérer d'abord."
            )
            return

        set_chenil(user_id, pokemon["name"])
        xp_evo = pokemon.get("xp_evo", 0)
        seuil  = f"`{pokemon.get('current_xp', 0)} / {xp_evo} XP`" if xp_evo > 0 else "pas d'évolution"
        minutes_par_tranche = SECONDES_PAR_TRANCHE // 60

        await ctx.send(
            f"🏠 **{pokemon['name']}** a été déposé au chenil !\n"
            f"⚡ Il gagnera **{XP_PAR_TRANCHE} XP** toutes les **{minutes_par_tranche} min** de vocal.\n"
            f"📊 XP actuel : {seuil}"
        )

    @commands.command(name="retirer_chenil")
    async def retirer_chenil_cmd(self, ctx):
        user_id = str(ctx.author.id)
        entry   = get_chenil(user_id)
        if not entry:
            await ctx.send("❌ Tu n'as aucun Pokémon au chenil.")
            return

        remove_chenil(user_id)
        pokemon = next(
            (p for p in get_new_captures(user_id)
             if p["name"].lower() == entry["pokemon_name"].lower()),
            None
        )
        xp_info = f"\n📊 XP actuel : `{pokemon['current_xp']} / {pokemon['xp_evo']}`" if pokemon else ""
        await ctx.send(f"✅ **{entry['pokemon_name']}** a été retiré du chenil.{xp_info}")

    @commands.command(name="voir_chenil")
    async def voir_chenil_cmd(self, ctx):
        user_id = str(ctx.author.id)
        entry   = get_chenil(user_id)
        if not entry:
            await ctx.send("🏠 Ton chenil est vide. Utilise `!chenil <nom>` pour y déposer un Pokémon.")
            return

        pokemon = next(
            (p for p in get_new_captures(user_id)
             if p["name"].lower() == entry["pokemon_name"].lower()),
            None
        )
        minutes_restantes   = entry["vocal_seconds"] // 60
        minutes_par_tranche = SECONDES_PAR_TRANCHE // 60
        temps_info = f"\n⏱️ Temps vocal en cours : `{minutes_restantes} min / {minutes_par_tranche} min`" \
                     if entry["vocal_seconds"] > 0 else ""

        if pokemon:
            xp_evo = pokemon.get("xp_evo", 0)
            seuil  = f"`{pokemon['current_xp']} / {xp_evo} XP`" if xp_evo > 0 else "pas d'évolution"
            await ctx.send(
                f"🏠 Au chenil : **{pokemon['name']}**\n"
                f"📊 XP : {seuil}{temps_info}\n"
                f"⚡ Gain : **{XP_PAR_TRANCHE} XP** toutes les **{minutes_par_tranche} min** de vocal"
            )
        else:
            await ctx.send(f"🏠 Au chenil : **{entry['pokemon_name']}**\n⚠️ Pokémon introuvable.{temps_info}")


# ── Fonction d'enregistrement ─────────────────────────────────────────────────

async def setup_chenil(bot):
    await bot.add_cog(ChenilCog(bot))