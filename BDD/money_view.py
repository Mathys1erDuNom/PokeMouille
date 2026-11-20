# money_view.py (migré dans BDD)
import discord
from utils import is_croco

from .money_db import get_balance, add_money, remove_money, set_money, transfer_money, cur


def setup_money(bot):
    """Configure toutes les commandes liées à l'argent."""
    
    @bot.command(name="money")
    async def money(ctx, user: discord.User = None):
        target = user or ctx.author
        balance = get_balance(target.id)
        
        if target == ctx.author:
            await ctx.send(f"💰🐊 Vous avez **{balance:,}** Croco dollars.")
        else:
            await ctx.send(f"💰🐊 {target.mention} a **{balance:,}** Croco dollars.")
    
    @is_croco()
    @bot.command(name="addmoney")
    async def addmoney(ctx, user: discord.User, amount: int):
        if amount <= 0:
            await ctx.send("❌ Le montant doit être positif.")
            return
        
        new_balance = add_money(user.id, amount)
        await ctx.send(
            f"✅ **{amount:,}** Croco dollars ont été ajoutées à {user.mention}.\n"
            f"💰🐊 Nouveau solde : **{new_balance:,}** Croco dollars."
        )
    
    @is_croco()
    @bot.command(name="removemoney")
    async def takemoney(ctx, user: discord.User, amount: int):
        if amount <= 0:
            await ctx.send("❌ Le montant doit être positif.")
            return
        
        success = remove_money(user.id, amount)
        
        if not success:
            balance = get_balance(user.id)
            await ctx.send(
                f"❌ {user.mention} tu es pauvre, tu n'as pas assez de Croco dollars.\n"
                f"💰🐊 Solde actuel : **{balance:,}** Croco dollars."
            )
        else:
            new_balance = get_balance(user.id)
            await ctx.send(
                f"✅ **{amount:,}** Croco dollars ont été retirées à {user.mention}.\n"
                f"💰🐊 Nouveau solde : **{new_balance:,}** Croco dollars."
            )
    
    @is_croco()
    @bot.command(name="setmoney")
    async def setmoney(ctx, user: discord.User, amount: int):
        if amount < 0:
            await ctx.send("❌ Le montant ne peut pas être négatif.")
            return
        
        set_money(user.id, amount)
        await ctx.send(
            f"✅ Le solde de {user.mention} a été défini à **{amount:,}** Croco dollars."
        )
    
    @bot.command(name="pay")
    async def pay(ctx, user: discord.User, amount: int):
        if amount <= 0:
            await ctx.send("❌ Le montant doit être positif.")
            return
        
        if user == ctx.author:
            await ctx.send("❌ Vous ne pouvez pas vous envoyer de l'argent à vous-même.")
            return
        
        success = transfer_money(ctx.author.id, user.id, amount)
        
        if not success:
            balance = get_balance(ctx.author.id)
            await ctx.send(
                f"❌ Sale pauvre, tu n'as pas assez de Croco dollars.\n"
                f"💰🐊 Votre solde : **{balance:,}** Croco dollars."
            )
        else:
            sender_balance = get_balance(ctx.author.id)
            receiver_balance = get_balance(user.id)
            await ctx.send(
                f"✅ Vous avez envoyé **{amount:,}** Croco dollars à {user.mention}.\n"
                f"💰🐊 Votre nouveau solde : **{sender_balance:,}** Croco dollars.\n"
                f"💰🐊 Solde de {user.mention} : **{receiver_balance:,}** Croco dollars."
            )
    
    @bot.command(name="richest")
    async def richest(ctx, limit: int = 10):
        if limit > 25:
            limit = 25
        
        cur.execute("""
            SELECT user_id, balance
            FROM argent
            ORDER BY balance DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        
        if not rows:
            await ctx.send("📊 Aucun utilisateur n'a d'argent pour le moment.")
            return
        
        embed = discord.Embed(
            title="🏆 Classement des plus riches",
            color=discord.Color.gold()
        )
        
        description = ""
        for i, (user_id, balance) in enumerate(rows, 1):
            try:
                user = await bot.fetch_user(int(user_id))
                username = user.name
            except:
                username = f"Utilisateur {user_id}"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} **{username}** — {balance:,} Croco dollars\n"
        
        embed.description = description
        await ctx.send(embed=embed)
