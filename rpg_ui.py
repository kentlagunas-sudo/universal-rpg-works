import streamlit as st
import random
import json
import ast
from openai import OpenAI

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(page_title="Universal RPG", page_icon="🎲", layout="wide")

# --- AI SETUP (Player2 Cloud Connection) ---
# Pulls your API key securely from Streamlit Cloud's secret vault!
try:
    PLAYER2_API_KEY = st.secrets["PLAYER2_API_KEY"]
except:
    PLAYER2_API_KEY = "PASTE_YOUR_PLAYER2_API_KEY_HERE_IF_TESTING_LOCALLY"

client = OpenAI(
    base_url="https://api.player2.game/v1",
    api_key=PLAYER2_API_KEY
)

MODEL_NAME = "default" 

SYSTEM_PROMPT = "You are an expert Game Master for a gritty, fiction-first RPG. Read the [SYSTEM DATA] for mechanical state, but NEVER read it out loud. Respond ONLY with immersive, cinematic narrative addressing the player directly. If the system data shows a roll result, narrate the outcome based on that. End every response by asking 'What do you do?'"

# --- STARTUP CHECK ---
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "bag" not in st.session_state:
    st.session_state.bag = []

# ==========================================
#         SCREEN 1: MAIN MENU
# ==========================================
if not st.session_state.game_started:
    st.title("🌌 Universal RPG: New Game")
    st.markdown("Welcome to the engine. Define your character and world below.")
    st.divider()
    
    char_name = st.text_area("Character Name & Deep Background:", placeholder="e.g., Jonathan Cross, 38. Orphaned in 1420, trained by the Vatican. He carries a cursed silver sword...")
    setting = st.text_area("Game Setting & Vibe:", placeholder="e.g., 1446 winter in an English village, tracking The Red Lady, Anne Rice gothic horror style...")
    
    if st.button("Start Adventure", type="primary"):
        if not char_name.strip():
            char_name = "Unknown Wanderer"
            
        st.session_state.character_name_full = char_name
        st.session_state.setting = setting
        
        st.session_state.inventory = []
        st.session_state.bag = []
        st.session_state.traits = []
        st.session_state.consequences = []
        st.session_state.wealth = "Struggling"
        st.session_state.enemy_name = None
        st.session_state.enemy_breakpoints = 0
        
        st.session_state.display_messages = []
        st.session_state.api_history = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        with st.spinner("Player2 AI is conjuring the world..."):
            setup_prompt = f"""
            Initialize a new game. 
            Full Character Lore: {char_name}
            Setting: {setting}
            
            You must output your response in two parts.
            
            PART 1:
            SUMMARY: "Create a short 3 to 6 word title for the UI (e.g., Jonathan Cross (38) - Hunter)"
            ITEMS: ["item1", "item2", "item3"]
            TRAITS: ["Trait Name: Short description", "Trait Name: Short description"]
            WEALTH: "Tier name (e.g., Struggling, Comfortable, Destitute, Wealthy)"
            STATS: {{"Force": X, "Finesse": Y, "Intellect": Z, "Spirit": W}}
            
            CRITICAL RULE FOR STATS: Assign numbers strictly between -1 and +2.
            
            PART 2:
            [NARRATIVE]
            Write the immersive opening scene describing the world and starting situation, ending with "What do you do?"
            """
            
            st.session_state.api_history.append({"role": "user", "content": setup_prompt})
            
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.api_history
                )
                full_text = response.choices[0].message.content
                st.session_state.api_history.append({"role": "assistant", "content": full_text})
                
                if "[NARRATIVE]" in full_text:
                    sys_data, narrative = full_text.split("[NARRATIVE]", 1)
                else:
                    sys_data = full_text
                    clean_lines = [l for l in full_text.split('\n') if not any(k in l for k in ["SUMMARY:", "ITEMS:", "TRAITS:", "WEALTH:", "STATS:"])]
                    narrative = "\n".join(clean_lines).strip()
                
                narrative = narrative.strip()
                
                for line in sys_data.split('\n'):
                    if "SUMMARY:" in line:
                        try:
                            st.session_state.char_summary = line.replace("SUMMARY:", "").strip().strip('"\'')
                        except: pass
                    if "WEALTH:" in line:
                        try:
                            st.session_state.wealth = line.replace("WEALTH:", "").strip().strip('"\'')
                        except: pass
                
                for line in sys_data.split("]"): 
                    line = line + "]" 
                    if "ITEMS:" in line:
                        try:
                            start = line.find("[")
                            end = line.find("]") + 1
                            generated_items = ast.literal_eval(line[start:end])
                            for item in generated_items:
                                if len(st.session_state.inventory) < 5:
                                    st.session_state.inventory.append(item)
                                elif len(st.session_state.bag) < 5:
                                    st.session_state.bag.append(item)
                        except: pass
                    if "TRAITS:" in line:
                        try:
                            start = line.find("[")
                            end = line.find("]") + 1
                            st.session_state.traits = ast.literal_eval(line[start:end])
                        except: pass
                        
                for line in sys_data.split('\n'):
                    if "STATS:" in line:
                        try:
                            start = line.find("{")
                            end = line.find("}") + 1
                            raw_stats = ast.literal_eval(line[start:end])
                            st.session_state.attributes = {}
                            for stat_key, val in raw_stats.items():
                                st.session_state.attributes[stat_key] = max(-1, min(int(val), 2))
                        except: pass

            except Exception as e:
                print(f"Parsing error: {e}")
                st.session_state.inventory = ["silver dagger", "travel cloak"]
                st.session_state.bag = []
                st.session_state.traits = ["Keen Instincts: Heightened awareness of danger."]
                st.session_state.wealth = "Struggling"
                st.session_state.char_summary = "Unknown Wanderer"
                st.session_state.attributes = {"Force": 1, "Finesse": 1, "Intellect": 0, "Spirit": 0}
                narrative = "The world forms around you in darkness. What do you do?"

            if not hasattr(st.session_state, 'char_summary'):
                st.session_state.char_summary = "Unknown Wanderer"
            if not hasattr(st.session_state, 'attributes') or not st.session_state.attributes:
                st.session_state.attributes = {"Force": 1, "Finesse": 1, "Intellect": 0, "Spirit": 0}
            if not st.session_state.inventory:
                st.session_state.inventory = ["trusted weapon"]
            if not hasattr(st.session_state, 'traits') or not st.session_state.traits:
                st.session_state.traits = ["Keen Instincts"]
            if not hasattr(st.session_state, 'wealth'):
                st.session_state.wealth = "Struggling"

            st.session_state.display_messages.append({"role": "assistant", "content": narrative})
        
        st.session_state.game_started = True
        st.rerun()

# ==========================================
#         SCREEN 2: ACTIVE GAME
# ==========================================
else:
    stat_synonyms = {
        "force": "Force", "strength": "Force", "power": "Force", "smash": "Force",
        "finesse": "Finesse", "speed": "Finesse", "agility": "Finesse", "stealth": "Finesse",
        "intellect": "Intellect", "logic": "Intellect", "mind": "Intellect", "investigate": "Intellect",
        "spirit": "Spirit", "will": "Spirit", "magic": "Spirit", "presence": "Spirit"
    }

    # --- THE SIDEBAR (Your HUD) ---
    with st.sidebar:
        st.title("🛡️ Character Sheet")
        st.markdown(f"### {st.session_state.char_summary}")
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Force", value=st.session_state.attributes.get("Force", 0))
            st.metric(label="Intellect", value=st.session_state.attributes.get("Intellect", 0))
        with col2:
            st.metric(label="Finesse", value=st.session_state.attributes.get("Finesse", 0))
            st.metric(label="Spirit", value=st.session_state.attributes.get("Spirit", 0))
            
        st.divider()
        st.markdown(f"### 🪙 Wealth: **{st.session_state.wealth}**")

        st.divider()
        st.markdown("### ✨ Traits & Abilities")
        if not st.session_state.traits:
            st.caption("None")
        else:
            for trait in st.session_state.traits:
                st.markdown(f"- **{trait}**")

        st.divider()
        st.markdown("### 🎒 Pockets / Belt (Max 5)")
        if len(st.session_state.inventory) == 0:
            st.caption("Empty")
        else:
            for item in st.session_state.inventory:
                st.markdown(f"- {item.title()}")

        st.divider()
        st.markdown("### 📦 Bag / Saddlebag (Max 5)")
        if len(st.session_state.bag) == 0:
            st.caption("Empty")
        else:
            for item in st.session_state.bag:
                st.markdown(f"- {item.title()}")
                
        st.divider()
        st.markdown("### 🩸 Consequences")
        if len(st.session_state.consequences) == 0:
            st.caption("Healthy")
        else:
            for cond in st.session_state.consequences:
                st.error(f"- {cond.title()}")
                
        if st.session_state.enemy_name:
            st.divider()
            st.markdown("### ⚔️ ACTIVE THREAT")
            st.warning(f"**{st.session_state.enemy_name.upper()}**\n\nHP: {'💀' * st.session_state.enemy_breakpoints}")

        # --- SYSTEM CONTROLS ---
        st.divider()
        st.markdown("### ⚙️ System")
        
        if st.button("💾 Save", use_container_width=True):
            save_data = {
                "character_name_full": st.session_state.character_name_full,
                "char_summary": st.session_state.char_summary,
                "setting": st.session_state.setting,
                "attributes": st.session_state.attributes,
                "traits": st.session_state.traits,
                "wealth": st.session_state.wealth,
                "inventory": st.session_state.inventory,
                "bag": st.session_state.bag,
                "consequences": st.session_state.consequences,
                "enemy_name": st.session_state.enemy_name,
                "enemy_breakpoints": st.session_state.enemy_breakpoints,
                "display_messages": st.session_state.display_messages,
                "api_history": st.session_state.api_history
            }
            try:
                with open("savegame.json", "w") as file:
                    json.dump(save_data, file)
                st.toast("Game Saved Successfully!", icon="✅")
            except Exception as e:
                st.error(f"Save failed: {e}")
                
        if st.button("🔄 New Game", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- MAIN SCREEN (The Chat UI) ---
    st.title("Universal RPG")

    for msg in st.session_state.display_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- THE INPUT ENGINE ---
    if prompt := st.chat_input("What do you do?"):
        
        st.session_state.display_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        command = prompt.lower()
        trigger_ai = False
        mechanics_summary = "Pure narrative action. No dice rolled."
        
        if command.startswith("spawn "):
            words = command.split()
            if len(words) >= 3:
                try:
                    st.session_state.enemy_breakpoints = int(words[-1])
                    st.session_state.enemy_name = " ".join(words[1:-1])
                    st.success(f"Threat Appeared: {st.session_state.enemy_name.title()}")
                    st.rerun()
                except:
                    pass
                    
        elif command.startswith("get ") or command.startswith("take "):
            item = command[4:].strip() if command.startswith("get ") else command[5:].strip()
            
            if len(st.session_state.inventory) < 5:
                st.session_state.inventory.append(item)
                st.toast(f"Added {item.title()} to Pockets!")
                st.rerun()
            elif len(st.session_state.bag) < 5:
                st.session_state.bag.append(item)
                st.toast(f"Pockets full! Added {item.title()} to Bag!")
                st.rerun()
            else:
                st.error("Both your pockets and your bag are full!")
                
        elif command.startswith("drop "):
            item = command[5:].strip()
            dropped = False
            for container in (st.session_state.inventory, st.session_state.bag):
                for idx, val in enumerate(container):
                    if val.lower() == item:
                        container.pop(idx)
                        dropped = True
                        break
                if dropped: break
                
            if dropped:
                st.toast(f"Dropped {item.title()}")
                st.rerun()
            else:
                st.toast(f"You don't have a '{item.title()}' to drop.")
                
        elif command.startswith("suffer "):
            cond = command[7:].strip()
            if len(st.session_state.consequences) < 4:
                st.session_state.consequences.append(cond)
                st.toast(f"Suffered consequence: {cond.title()}", icon="🩸")
                st.rerun()
                
        else:
            chosen_stat = None
            for word in command.split():
                clean = word.strip(".,!?")
                if clean in stat_synonyms:
                    chosen_stat = stat_synonyms[clean]
                    break
                    
            if chosen_stat:
                modifier = st.session_state.attributes.get(chosen_stat, 0)
                is_adv = "adv" in command
                is_dis = "dis" in command
                
                if is_adv:
                    dice = sorted([random.randint(1, 6) for _ in range(3)], reverse=True)[:2]
                elif is_dis:
                    dice = sorted([random.randint(1, 6) for _ in range(3)])[:2]
                else:
                    dice = [random.randint(1, 6), random.randint(1, 6)]
                    
                roll_total = sum(dice)
                final_total = roll_total + modifier
                
                st.info(f"**Rolled {chosen_stat}:** {dice} + {modifier} = **{final_total}**")
                
                damage = 0
                if final_total >= 12:
                    result_str = "CRITICAL SUCCESS"
                    damage = 2
                elif final_total >= 10:
                    result_str = "STRONG SUCCESS"
                    damage = 1
                elif final_total >= 7:
                    result_str = "MIXED SUCCESS (Player suffers setback/minor consequence)"
                    damage = 1
                else:
                    result_str = "MISS (Player suffers major consequence)"
                    damage = 0
                    
                if st.session_state.enemy_name and damage > 0:
                    st.session_state.enemy_breakpoints -= damage
                    if st.session_state.enemy_breakpoints <= 0:
                        result_str += f" - THE {st.session_state.enemy_name.upper()} IS KILLED/DESTROYED!"
                        st.session_state.enemy_name = None
                        st.session_state.enemy_breakpoints = 0
                        
                mechanics_summary = f"Player rolled {chosen_stat}. Total: {final_total}. Outcome: {result_str}."
                trigger_ai = True
            else:
                trigger_ai = True

        if trigger_ai:
            with st.chat_message("assistant"):
                with st.spinner("Player2 AI is writing..."):
                    
                    if len(st.session_state.api_history) > 11:
                        st.session_state.api_history = [st.session_state.api_history[0]] + st.session_state.api_history[-10:]

                    ai_prompt = f"""
                    [SYSTEM DATA]
                    Wealth: {st.session_state.wealth}
                    Consequences: {st.session_state.consequences}
                    Primary Inventory: {st.session_state.inventory}
                    Bag/Saddlebag: {st.session_state.bag}
                    Enemy: {st.session_state.enemy_name} (HP: {st.session_state.enemy_breakpoints})
                    Roll Result: {mechanics_summary}
                    
                    [PLAYER ACTION]
                    {command}
                    """
                    
                    st.session_state.api_history.append({"role": "user", "content": ai_prompt})
                    
                    try:
                        response = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=st.session_state.api_history
                        )
                        reply_text = response.choices[0].message.content
                        
                        st.session_state.api_history.append({"role": "assistant", "content": reply_text})
                        st.session_state.display_messages.append({"role": "assistant", "content": reply_text})
                        
                        st.markdown(reply_text)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Player2 API Error: {e}")
