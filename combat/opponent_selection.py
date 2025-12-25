import discord
from discord.ui import View, Select, Button
import json
from typing import List, Dict


class OpponentManager:
    """Gestionnaire des adversaires"""
    
    def __init__(self, json_path: str = "opponents.json"):
        self.json_path = json_path
        self.opponents = self._load_opponents()
    
    def _load_opponents(self) -> List[Dict]:
        """Charge les adversaires depuis le fichier JSON"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("opponents", [])
        except FileNotFoundError:
            print(f"Fichier {self.json_path} introuvable. Création d'un fichier par défaut.")
            self._create_default_file()
            return self._load_opponents()
        except json.JSONDecodeError:
            print(f"Erreur de lecture du fichier {self.json_path}")
            return []
    
    def _create_default_file(self):
        """Crée un fichier JSON par défaut"""
        default_data = {
            "opponents": [
                {
                    "id": "starter_trainer",
                    "name": "Dresseur Débutant",
                    "description": "Un dresseur qui débute",
                    "team": ["Bulbasaur", "Charmander", "Squirtle"],
                    "difficulty": "⭐"
                }
            ]
        }
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
    
    def get_opponent_by_id(self, opponent_id: str) -> Dict:
        """Récupère un adversaire par son ID"""
        for opponent in self.opponents:
            if opponent.get("id") == opponent_id:
                return opponent
        return None
    
    def get_all_opponents(self) -> List[Dict]:
        """Retourne tous les adversaires"""
        return self.opponents


class OpponentSelectMenu(Select):
    """Menu de sélection d'adversaire"""
    
    def __init__(self, opponents: List[Dict], parent_view: "OpponentSelectionView"):
        # Créer les options pour le menu
        options = [
            discord.SelectOption(
                label=opp["name"],
                value=opp["id"],
                description=f"{opp['difficulty']} - {opp['description'][:50]}",
                emoji="⚔️"
            )
            for opp in opponents[:25]  # Max 25 options
        ]
        
        super().__init__(
            placeholder="Choisis ton adversaire...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="opponent_select",
            row=0
        )
        self.parent_view = parent_view
        self.opponents = {opp["id"]: opp for opp in opponents}
    
    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]
        opponent = self.opponents.get(selected_id)
        
        if opponent:
            self.parent_view.selected_opponent = opponent
            
            # Affiche les détails de l'adversaire
            embed = discord.Embed(
                title=f"⚔️ {opponent['name']}",
                description=opponent['description'],
                color=discord.Color.red()
            )
            embed.add_field(
                name="Difficulté",
                value=opponent['difficulty'],
                inline=True
            )
            embed.add_field(
                name="Équipe",
                value=", ".join(opponent['team']),
                inline=False
            )
            
            await interaction.response.edit_message(
                content="Adversaire sélectionné ! Confirme ton choix :",
                embed=embed,
                view=self.parent_view
            )


class ConfirmButton(Button):
    """Bouton de confirmation du choix d'adversaire"""
    
    def __init__(self, parent_view: "OpponentSelectionView"):
        super().__init__(
            label="✅ Confirmer et choisir mon équipe",
            style=discord.ButtonStyle.success,
            row=1
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        if not self.parent_view.selected_opponent:
            await interaction.response.send_message(
                "❌ Tu dois d'abord sélectionner un adversaire.",
                ephemeral=True
            )
            return
        
        # Appelle le callback de confirmation
        await self.parent_view.on_confirm(interaction)


class CancelButton(Button):
    """Bouton d'annulation"""
    
    def __init__(self):
        super().__init__(
            label="❌ Annuler",
            style=discord.ButtonStyle.danger,
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Combat annulé.",
            embed=None,
            view=None
        )


class OpponentSelectionView(View):
    """Vue de sélection d'adversaire"""
    
    def __init__(self, opponents: List[Dict], on_confirm_callback):
        super().__init__(timeout=180)
        self.selected_opponent = None
        self.on_confirm_callback = on_confirm_callback
        
        # Ajoute les composants
        self.add_item(OpponentSelectMenu(opponents, self))
        self.add_item(ConfirmButton(self))
        self.add_item(CancelButton())
    
    async def on_confirm(self, interaction: discord.Interaction):
        """Appelé quand l'utilisateur confirme son choix"""
        await self.on_confirm_callback(interaction, self.selected_opponent)