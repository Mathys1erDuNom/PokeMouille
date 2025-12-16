# money_commands.py
import discord
from money_db import get_balance, add_money, remove_money, set_money, transfer_money
from utils import is_croco


def setup_money(bot):
    """Configure toutes les commandes liées à l'argent."""
    
    @bot.command(name="money")
    async def money(ctx, user: discord.User = None):
        """Affiche le solde d'un utilisateur."""
        target = user or ctx.author
        balance = get_balance(target.id)
        
        if target == ctx.author:
            await ctx.send(f"💰 Vous avez **{balance:,}** pièces d'or.")
        else:
            await ctx.send(f"💰 {target.mention} a **{balance:,}** pièces d'or.")
    
    
    @bot.command(name="balance")
    async def balance(ctx, user: discord.User = None):
        """Alias de !money."""
        target = user or ctx.author
        balance = get_balance(target.id)
        
        if target == ctx.author:
            await ctx.send(f"💰 Vous avez **{balance:,}** pièces d'or.")
        else:
            await ctx.send(f"💰 {target.mention} a **{balance:,}** pièces d'or.")
    
    
    @is_croco()
    @bot.command(name="addmoney")
    async def addmoney(ctx, user: discord.User, amount: int):
        """Ajoute de l'argent à un utilisateur (admin uniquement)."""
        if amount <= 0:
            await ctx.send("❌ Le montant doit être positif.")
            return
        
        new_balance = add_money(user.id, amount)
        await ctx.send(
            f"✅ Grand Maître suprême des Crocodiles, **{amount:,}** pièces d'or ont été ajoutées à {user.mention}.\n"
            f"💰 Nouveau solde : **{new_balance:,}** pièces."
        )
    
    
    @is_croco()
    @bot.command(name="removemoney")
    async def removemoney(ctx, user: discord.User, amount: int):
        """Retire de l'argent à un utilisateur (admin uniquement)."""
        if amount <= 0:
            await ctx.send("❌ Le montant doit être positif.")
            return
        
        success = remove_money(user.id, amount)
        
        if not success:
            balance = get_balance(user.id)
            await ctx.send(
                f"❌ Grand Maître suprême des Crocodiles, {user.mention} n'a pas assez d'argent.\n"
                f"💰 Solde actuel : **{balance:,}** pièces."
            )
        else:
            new_balance = get_balance(user.id)
            await ctx.send(
                f"✅ Grand Maître suprême des Crocodiles, **{amount:,}** pièces d'or ont été retirées à {user.mention}.\n"
                f"💰 Nouveau solde : **{new_balance:,}** pièces."
            )
    
    
    @is_croco()
    @bot.command(name="setmoney")
    async def setmoney(ctx, user: discord.User, amount: int):
        """Définit le solde exact d'un utilisateur (admin uniquement)."""
        if amount < 0:
            await ctx.send("❌ Le montant ne peut pas être négatif.")
            return
        
        set_money(user.id, amount)
        await ctx.send(
            f"✅ Grand Maître suprême des Crocodiles, le solde de {user.mention} a été défini à **{amount:,}** pièces d'or."
        )
    
    
    @bot.command(name="pay")
    async def pay(ctx, user: discord.User, amount: int):
        """Transfère de l'argent à un autre utilisateur."""
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
                f"❌ Vous n'avez pas assez d'argent pour effectuer ce transfert.\n"
                f"💰 Votre solde : **{balance:,}** pièces."
            )
        else:
            sender_balance = get_balance(ctx.author.id)
            receiver_balance = get_balance(user.id)
            await ctx.send(
                f"✅ Vous avez envoyé **{amount:,}** pièces d'or à {user.mention}.\n"
                f"💰 Votre nouveau solde : **{sender_balance:,}** pièces.\n"
                f"💰 Solde de {user.mention} : **{receiver_balance:,}** pièces."
            )
    
    
    @bot.command(name="richest")
    async def richest(ctx, limit: int = 10):
        """Affiche le classement des utilisateurs les plus riches."""
        from money_db import cur
        
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
            description += f"{medal} **{username}** — {balance:,} pièces\n"
        
        embed.description = description
        await ctx.send(embed=embed)