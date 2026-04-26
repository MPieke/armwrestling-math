# Ermes vs Morozov Mechanism Atoms

Generated: 2026-04-26T18:58:06.857169+00:00
Model: `gpt-5-nano`
Input claims: `115`
Atoms: `69`
Estimated OpenAI cost: `$0.0231`

This artifact decomposes claims into granular armwrestling mechanisms. Raw claims remain
the source of truth; atoms are indexing and reasoning aids.

## Summary

- Actors: `{'Morozov': 3, 'Ermes': 4, 'Ermes Gasparini': 28, 'Other/unknown': 5, 'Artyom Morozov': 3, 'Jerry Cadorette': 2, 'Levan Saginashvili': 4, 'Armwrestling Newz': 8, 'Devon Larratt': 4, 'Engin Terzi': 1, 'Commentator': 7}`
- Top actions: `{'back_pressure': 7, 'rise': 4, 'top_roll': 3, 'elbow_flexion': 3, 'press': 2, 'wrist_control_unspecified': 2, 'shoulder pressure': 2, 'inside_hook': 2, 'flop_press_transition': 2, 'pronation': 2, 'cup_deep_grip': 1, 'open_fingers': 1, 'hook': 1, 'start_position_advantage': 1, 'no_prestep_movement': 1, 'hand size advantage; static strength': 1, 'shoulder pressure (sustained)': 1, 'psychological state: anger/hunger': 1, 'hand control near pad': 1, 'wrist control': 1}`
- Lanes: `{'unknown': 27, 'outside/toproll': 11, 'inside/hook': 10, 'press': 7, 'side pressure': 3, 'center_table_hook': 2, 'flop press': 1, 'side pressure|press': 1, 'inside/hook|toproll': 1, 'press|side pressure': 1, 'defensive_stop': 1, 'strap': 1, 'center_table': 1}`

## Mechanism Conflicts

### Ermes outside/pronation access vs Morozov cup/contain/hook access

This is the key lane clash: Ermes needs height/pronation/back-pressure access, while Morozov's hook threat depends on cupping or containing that access.

Side A atoms: `['a21_3', 'a22_4', 'a20_5', 'a27_6', 'a84_25', 'a90_1', 'a91_2', 'a98_9', 'a99_10', 'a103_14', 'a104_15', 'a109_20']`
Side B atoms: `['a3_1', 'a48_4']`
Unresolved: Can Morozov contain Ermes before Ermes climbs, rises, or transitions?

## Atom Library

### a3_1

Claim `3`: [05:15](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=315s) Artyom Morozov cups deep on his right arm.

Actor: `Morozov`. Action: `cup_deep_grip`. Lane: `inside/hook`. Position: ``.

Enables: `['hand_control', 'hook_possession']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a25_2

Claim `25`: [04:03](https://www.youtube.com/watch?v=yGBrHvylMWs&t=243s) Artyom Morozov managed to stop Vitaly Laletin with only back pressure, even after his arm was already cracking.

Actor: `Morozov`. Action: `back_pressure`. Lane: `press`. Position: ``.

Enables: `['stabilization', 'control_through_pressure']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a21_3

Claim `21`: [21:07](https://www.youtube.com/watch?v=28S8Qd02rxI&t=1267s) Ermes Gasparini explains that the first step of his top roll technique is to 'open the finger' of his opponent.

Actor: `Ermes`. Action: `open_fingers`. Lane: `outside/toproll`. Position: ``.

Enables: `['top_roll_transition', 'hand_control_break']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a22_4

Claim `22`: [22:32](https://www.youtube.com/watch?v=28S8Qd02rxI&t=1352s) Ermes Gasparini states that using a hook or side pressure is 'impossible' against Levan, and the only way is to 'open his wrist' with a top roll.

Actor: `Ermes`. Action: `top_roll`. Lane: `outside/toproll`. Position: ``.

Enables: `['wrist_opening', 'pronation_advantage', 'top_roll_effectiveness']`
Denies: `['hook_or_side_pressure_against_Levan']`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a20_5

Claim `20`: [15:59](https://www.youtube.com/watch?v=28S8Qd02rxI&t=959s) Ermes Gasparini claims Dave Chaffee has 'never felt the top roll like me,' emphasizing his unique wrist and pronation technique.

Actor: `Ermes`. Action: `top_roll`. Lane: `outside/toproll`. Position: ``.

Enables: `['wrist_control', 'pronation_advantage']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a27_6

Claim `27`: [01:8:06](https://www.youtube.com/watch?v=yGBrHvylMWs&t=4086s) Attacking Michael Todd directly with a top roll is very dangerous for the wrist and side pressure, a strategy Ermes Gasparini correctly avoided.

Actor: `Ermes`. Action: `top_roll`. Lane: `outside/toproll`. Position: ``.

Enables: `['wrist_injury_avoidance', 'side_pressure_safety']`
Denies: `['unsafe_wrist_side_pressure']`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a30_1

Claim `30`: [02:45](https://www.youtube.com/watch?v=yGBrHvylMWs&t=165s) Ermes Gasparini's shoulder press is stronger than Vitaly Laletin's, partly due to Ermes's slightly shorter arm providing a leverage advantage.

Actor: `Ermes Gasparini`. Action: `press`. Lane: `unknown`. Position: ``.

Enables: `['leverage_advantage', 'shoulder_press_power']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: Arm-length leverage is suggested as factor; not a direct match event.

### a31_2

Claim `31`: [02:57](https://www.youtube.com/watch?v=yGBrHvylMWs&t=177s) Engin Terzi notes that Vitaly Laletin has struggled with wrist control against opponents like Ferit Osmanli, Zaur, and Ermes Gasparini, indicating his wrist is not unbreakable.

Actor: `Other/unknown`. Action: `wrist_control_unspecified`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: Wrist control mechanism not specified.

### a34_3

Claim `34`: [67:00](https://www.youtube.com/watch?v=nvlNtq3T-Hw&t=4020s) Post-surgery, Morozov's 'rising' strength on his right hand does not drop or fatigue as it did before.

Actor: `Artyom Morozov`. Action: `rise`. Lane: `outside/toproll`. Position: `defensive`.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `True`. Durable style: `True`. Historical: `True`.
Caveat: Rising strength described as defensive/offensive component against top-roll.

### a48_4

Claim `48`: [01:13](https://www.youtube.com/watch?v=U0kDxaszCu8&t=73s) Artyom Morozov's hook is 'super strong.'

Actor: `Artyom Morozov`. Action: `hook`. Lane: `inside/hook`. Position: ``.

Enables: `['hook_strength']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: Based on Ermes' comment; not direct observation of Morozov's hook in this match.

### a49_5

Claim `49`: [01:18](https://www.youtube.com/watch?v=U0kDxaszCu8&t=78s) Jerry can win if he gets his position faster than Morozov.

Actor: `Jerry Cadorette`. Action: `start_position_advantage`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: Starts advantage; no direct start sequence observed here.

### a50_6

Claim `50`: [01:28](https://www.youtube.com/watch?v=U0kDxaszCu8&t=88s) Jerry's press is a serious threat, citing his match where he pressed back against Genadi Kvikvinia.

Actor: `Jerry Cadorette`. Action: `press`. Lane: `press`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: Press as threat; observed match evidence.

### a45_7

Claim `45`: [41:48](https://www.youtube.com/watch?v=bZUOAv0Kzxs&t=2508s) Morozov values fair, mutual starts with no pre-start movement. He believes if the match starts fairly, the stronger one will win, and considers cheating unfair.

Actor: `Morozov`. Action: `no_prestep_movement`. Lane: `unknown`. Position: ``.

Enables: `['start_fairness']`
Denies: `['pre_start_movement_cheating']`
Follow-up: `[]`
Condition: 
Current form usable: `True`. Durable style: `True`. Historical: `True`.
Caveat: Morozov's stance on starts; not a specific technique used in match.

### a60_1

Claim `60`: [21:08](https://www.youtube.com/watch?v=HBfb57rQxTg&t=1268s) Levan notes Denis possesses a 'huge hand' and 'very good static' that could challenge Ermes's wrist.

Actor: `Levan Saginashvili`. Action: `hand size advantage; static strength`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a61_2

Claim `61`: [21:21](https://www.youtube.com/watch?v=HBfb57rQxTg&t=1281s) Levan states Ermes '100% need to shoulder pressure' to defeat Denis.

Actor: `Levan Saginashvili`. Action: `shoulder pressure`. Lane: `side pressure`. Position: ``.

Enables: `['shoulder-pressure-based defeat plan']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a62_3

Claim `62`: [21:37](https://www.youtube.com/watch?v=HBfb57rQxTg&t=1297s) Levan believes if Ermes 'continues again and again' with shoulder pressure, he would win.

Actor: `Levan Saginashvili`. Action: `shoulder pressure (sustained)`. Lane: `side pressure`. Position: ``.

Enables: `['win by sustained shoulder pressure']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a63_4

Claim `63`: [21:53](https://www.youtube.com/watch?v=HBfb57rQxTg&t=1313s) Levan notes Denis is 'very angry and hungry' after losing to Devon.

Actor: `Levan Saginashvili`. Action: `psychological state: anger/hunger`. Lane: ``. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a64_5

Claim `64`: [00:25](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=25s) Ermes gained hand control very near the pad and successfully brought Dave back to the center.

Actor: `Ermes Gasparini`. Action: `hand control near pad`. Lane: `unknown`. Position: `center`.

Enables: `['center-table recovery']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a65_6

Claim `65`: [01:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=60s) Ermes gets behind his shoulder to press immediately after regaining center.

Actor: `Ermes Gasparini`. Action: `shoulder pressure`. Lane: `press`. Position: `regained_center`.

Enables: `['center-table pressure finish']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a66_7

Claim `66`: [01:35](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=95s) You cannot beat Ermes Gasparini if you have not taken his wrist.

Actor: `Armwrestling Newz`. Action: `wrist control`. Lane: `inside/hook`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a67_8

Claim `67`: [02:50](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=170s) Ermes brought Dave back to center with a single surge despite being less than an inch from being pinned.

Actor: `Ermes Gasparini`. Action: `center-table surge`. Lane: `press`. Position: `center`.

Enables: `['center positioning after surge']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a68_9

Claim `68`: [03:00](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=180s) Ermes has an incredibly fast flop press transition when his wrist is compromised.

Actor: `Ermes Gasparini`. Action: `flop press transition`. Lane: `press`. Position: ``.

Enables: `['flop press readiness when wrist compromised']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a69_10

Claim `69`: [03:10](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=190s) Ermes intentionally dumped his wrist to use the flop press as a tactical choice.

Actor: `Ermes Gasparini`. Action: `wrist dump`. Lane: `flop press`. Position: ``.

Enables: `['flop press tactic']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a70_11

Claim `70`: [04:05](https://www.youtube.com/watch?v=Fg5g-F7TwA4&t=245s) Ermes is likely the #2 armwrestler in the world following this performance.

Actor: `Armwrestling Newz`. Action: `ranking assertion: #2`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a71_12

Claim `71`: [00:10](https://www.youtube.com/watch?v=pHHR6Bc9zXY&t=10s) Devon believes Morozov vs Gennadi is a close match, highlighting Morozov's top roll vs Gennadi's inside game.

Actor: `Devon Larratt`. Action: `top roll`. Lane: `outside/toproll`. Position: ``.

Enables: `['top-roll against Morozov']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a72_13

Claim `72`: [01:40](https://www.youtube.com/watch?v=pHHR6Bc9zXY&t=100s) Ermes is no longer just a top-roller; he has developed significant shoulder pressure and a press.

Actor: `Devon Larratt`. Action: `shoulder pressure; press`. Lane: `side pressure|press`. Position: ``.

Enables: `['Ermes can win even if wrist is compromised']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a73_14

Claim `73`: [01:52](https://www.youtube.com/watch?v=pHHR6Bc9zXY&t=112s) Ermes' primary danger zone is being caught on his brachioradialis; if caught there, it is very hard to survive.

Actor: `Engin Terzi`. Action: `brachioradialis exposure`. Lane: `inside/hook`. Position: ``.

Enables: `['path to beat Ermes via hook/cup']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a74_15

Claim `74`: [02:15](https://www.youtube.com/watch?v=pHHR6Bc9zXY&t=135s) To beat a flop-presser, a puller must train supination and a low cup to pull the opponent out of their tricep.

Actor: `Devon Larratt`. Action: `supination training`. Lane: `unknown`. Position: ``.

Enables: `['defense against flop-presser']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a74_16

Claim `74`: [02:15](https://www.youtube.com/watch?v=pHHR6Bc9zXY&t=135s) To beat a flop-presser, a puller must train supination and a low cup to pull the opponent out of their tricep.

Actor: `Devon Larratt`. Action: `low cup training`. Lane: `unknown`. Position: ``.

Enables: `['defense against flop-presser']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a76_17

Claim `76`: [00:55](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=55s) Ermes Gasparini is competing at 130kg and is in peak form, having just defeated Dave Chaffee on the right hand.

Actor: `Commentator`. Action: `weight 130 kg bodyweight`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a77_18

Claim `77`: [01:50](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=110s) Artyom Morozov is coming off a significant right-hand victory over Revaz Lutidze.

Actor: `Commentator`. Action: `recent right-hand victory over Revaz Lutidze`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a78_19

Claim `78`: [03:00](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=180s) Morozov's wrist control 'up top' is described as phenomenal.

Actor: `Commentator`. Action: `wrist control up top`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a79_20

Claim `79`: [07:10](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=430s) Morozov's height and joint position allow him to apply massive pressure even when his wrist is technically compromised.

Actor: `Commentator`. Action: `pressure despite wrist compromise`. Lane: `press`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a80_21

Claim `80`: [07:25](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=445s) Ermes appeared to 'give up' his wrist or sacrifice position after failing to find a quick finish against Morozov's height.

Actor: `Commentator`. Action: `wrist surrender`. Lane: `unknown`. Position: ``.

Enables: `['defensive repositioning']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a81_22

Claim `81`: [11:30](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=690s) Morozov demonstrates a very efficient transition to side pressure and the pad once he secures hand position.

Actor: `Commentator`. Action: `transition to side pressure and pad`. Lane: `side pressure`. Position: ``.

Enables: `['finishing position after hand control']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a82_23

Claim `82`: [14:50](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=890s) Morozov is described as having the perfect frame for the sport and 'checking all the boxes' for long-term dominance.

Actor: `Commentator`. Action: `frame strength; dominance potential`. Lane: `unknown`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a83_24

Claim `83`: [16:10](https://www.youtube.com/watch?v=bWmtNWQM_Ro&t=970s) Morozov admits he was not fully confident in himself during the first round of the match.

Actor: `Artyom Morozov`. Action: `not fully confident in first round`. Lane: ``. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a84_25

Claim `84`: [00:45](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=45s) Ermes uses a hybrid drag and pivot move to punch his knuckle up and over the opponent's hand.

Actor: `Ermes Gasparini`. Action: `hybrid drag and pivot; knuckle up and over opponent's hand`. Lane: `outside/toproll`. Position: ``.

Enables: `["negation of Morozov's hand control; high-knuckle toproll"]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a85_26

Claim `85`: [01:40](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=100s) Ermes is consistently opening the opponent's elbow flexor angle through superior back pressure.

Actor: `Armwrestling Newz`. Action: `back pressure opens elbow flexor angle`. Lane: `inside/hook`. Position: ``.

Enables: `['defensive and offensive toproll success']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a86_27

Claim `86`: [02:50](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=170s) Ermes maintains a significantly tighter elbow flexor angle than elite opponents, keeping his knuckle higher throughout the pull.

Actor: `Armwrestling Newz`. Action: `tight elbow flexor angle; knuckle higher`. Lane: `inside/hook|toproll`. Position: ``.

Enables: `['effective toproll against Morozov']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a87_28

Claim `87`: [05:15](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=315s) Ermes shows a strong transition to a flop press when his elbow flexor begins to open or gas.

Actor: `Armwrestling Newz`. Action: `transition to flop press`. Lane: `press`. Position: ``.

Enables: `['Plan B if Morozov stops initial toproll']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a88_29

Claim `88`: [06:40](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=400s) Ermes utilizes shoulder commitment to decrease his elbow flexor angle and press through defensive positions.

Actor: `Armwrestling Newz`. Action: `shoulder commitment; press through defense`. Lane: `press|side pressure`. Position: ``.

Enables: `["counter to Morozov's defense"]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a89_30

Claim `89`: [08:15](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=495s) Ermes has specifically improved his ability to handle 'King's Move' and open toproll pressure.

Actor: `Armwrestling Newz`. Action: `handle King's Move`. Lane: `inside/hook`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `False`.
Caveat: 

### a89_31

Claim `89`: [08:15](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=495s) Ermes has specifically improved his ability to handle 'King's Move' and open toproll pressure.

Actor: `Armwrestling Newz`. Action: `open toproll pressure`. Lane: `outside/toproll`. Position: ``.

Enables: `[]`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `False`.
Caveat: 

### a90_1

Claim `90`: [08:45](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=525s) Ermes is focusing on gaining height and technical proficiency against long-armed pullers.

Actor: `Ermes Gasparini`. Action: `rise`. Lane: `unknown`. Position: ``.

Enables: `['height_gain_against_long_armed_pullers']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a91_2

Claim `91`: [09:45](https://www.youtube.com/watch?v=n_6pWpcJT1g&t=585s) Ermes looks technically better and more 'figured out' than in his previous elite match appearances.

Actor: `Ermes Gasparini`. Action: `rise`. Lane: `unknown`. Position: ``.

Enables: `['height_gain_against_variants_of_opponent']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a92_3

Claim `92`: [00:45](https://www.youtube.com/watch?v=drxsBp2g4BM&t=45s) Devon Larratt's strategy was to fight for height and create distance, making it impossible for Ermes to contain him.

Actor: `Other/unknown`. Action: `rise`. Lane: `unknown`. Position: ``.

Enables: `['height_advantage_for Morozov_to_stay_off_bottom']`
Denies: `['Morozov containment of Ermes']`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a93_4

Claim `93`: [01:40](https://www.youtube.com/watch?v=drxsBp2g4BM&t=100s) Devon was able to 'double cap' his thumb, indicating he had achieved superior height and supination in the setup.

Actor: `Other/unknown`. Action: `thumb_setup_supination`. Lane: `unknown`. Position: ``.

Enables: `['height_and_supination_in_setup']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a94_5

Claim `94`: [02:20](https://www.youtube.com/watch?v=drxsBp2g4BM&t=140s) Ermes' 95kg of back pressure is effectively neutralized the moment his wrist is forced back.

Actor: `Ermes Gasparini`. Action: `back_pressure`. Lane: `center_table_hook`. Position: ``.

Enables: `['neutralizes_back_pressure_when_wrist_forced_back']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a95_6

Claim `95`: [02:50](https://www.youtube.com/watch?v=drxsBp2g4BM&t=170s) Ermes consistently struggles with long-armed toprollers, as seen in his matches against Devon Larratt and Alex Kurdecha.

Actor: `Ermes Gasparini`. Action: `inside_hook_struggle`. Lane: `inside/hook`. Position: ``.

Enables: `['inside_pull_problems_for_morozov']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a96_7

Claim `96`: [03:10](https://www.youtube.com/watch?v=drxsBp2g4BM&t=190s) Ermes defeated Genadi Kvikvinia, proving he is extremely effective against high-level inside pullers.

Actor: `Other/unknown`. Action: `inside_hook`. Lane: `inside/hook`. Position: ``.

Enables: `['advantage_against_high_level_inside_pullers']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a97_8

Claim `97`: [03:30](https://www.youtube.com/watch?v=drxsBp2g4BM&t=210s) If an opponent does not challenge Ermes' height, he has full access to his side pressure and back pressure, making him nearly impossible to beat.

Actor: `Other/unknown`. Action: `inside_hook`. Lane: `unknown`. Position: ``.

Enables: `['Ermes_handling_in_inside_positions']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a98_9

Claim `98`: [01:55](https://www.youtube.com/watch?v=DtDtFv7bCVs&t=115s) Ermes's wrist tends to buckle back when he drives to the side against a strong open toproll.

Actor: `Ermes Gasparini`. Action: `wrist_control_unspecified`. Lane: `outside/toproll`. Position: ``.

Enables: `['cup_or_control_to_counter_open_toproll']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `True`. Durable style: `True`. Historical: `True`.
Caveat: 

### a99_10

Claim `99`: [02:10](https://www.youtube.com/watch?v=DtDtFv7bCVs&t=130s) Ermes possesses massive arm power and back pressure in his outside move.

Actor: `Ermes Gasparini`. Action: `back_pressure`. Lane: `outside/toproll`. Position: ``.

Enables: `['defensive_and_offensive_tool_in_outside_move']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `True`. Durable style: `True`. Historical: `True`.
Caveat: 

### a100_11

Claim `100`: [03:30](https://www.youtube.com/watch?v=DtDtFv7bCVs&t=210s) Ermes has a very effective flop press transition if his wrist is forced into a losing position.

Actor: `Ermes Gasparini`. Action: `flop_press_transition`. Lane: `unknown`. Position: ``.

Enables: `['transition_to_flop_press_when_wrist_compromised']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `True`. Durable style: `True`. Historical: `True`.
Caveat: 

### a101_12

Claim `101`: [04:40](https://www.youtube.com/watch?v=DtDtFv7bCVs&t=280s) Ermes demonstrates 'crazy' back pressure and side pressure even when pulled into a center-table hook.

Actor: `Ermes Gasparini`. Action: `back_pressure`. Lane: `center_table_hook`. Position: ``.

Enables: `['dominant_through_center_table_lane']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `True`. Durable style: `True`. Historical: `True`.
Caveat: 

### a102_13

Claim `102`: [05:00](https://www.youtube.com/watch?v=DtDtFv7bCVs&t=300s) Ermes shows high shoulder commitment and frame strength in inside positions.

Actor: `Ermes Gasparini`. Action: `shoulder_commitment_elbow_frame_strength`. Lane: `inside/hook`. Position: ``.

Enables: `['defensive_stability_against_frame_pressure']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `True`. Durable style: `True`. Historical: `True`.
Caveat: 

### a103_14

Claim `103`: [00:40](https://www.youtube.com/watch?v=5xm7odwrnZQ&t=40s) Levan's hand is too large to control using standard pronation and height through the index knuckle.

Actor: `Ermes Gasparini`. Action: `rising_through_thumb`. Lane: `unknown`. Position: ``.

Enables: `['counter_levan_hand_size_with_thumb_rise']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a104_15

Claim `104`: [00:50](https://www.youtube.com/watch?v=5xm7odwrnZQ&t=50s) The only realistic way to defeat a puller of Levan's caliber is through extreme back pressure and rising through the thumb.

Actor: `Ermes Gasparini`. Action: `back_pressure; rising_through_thumb`. Lane: `unknown`. Position: ``.

Enables: `['extremely_effective_defense_using_back_pressure_and_thumb_rise']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a105_16

Claim `105`: [01:50](https://www.youtube.com/watch?v=5xm7odwrnZQ&t=110s) Ermes' back pressure is significantly stronger than Devon Larratt's, allowing him to hold positions Devon cannot.

Actor: `Ermes Gasparini`. Action: `back_pressure`. Lane: `defensive_stop`. Position: ``.

Enables: `['holds_positions_against_stronger_opponents']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a106_17

Claim `106`: [02:05](https://www.youtube.com/watch?v=5xm7odwrnZQ&t=125s) Ermes found a specific spot inside the straps to stop Levan by pulling through the thumb and out the back.

Actor: `Ermes Gasparini`. Action: `pulling_through_thumb; strap_leverage`. Lane: `strap`. Position: ``.

Enables: `['strap_leverage_to_stop_levan']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a107_18

Claim `107`: [02:40](https://www.youtube.com/watch?v=5xm7odwrnZQ&t=160s) Ermes possesses elite elbow flexion that allows him to maintain a stop several inches above the pin line even when his wrist is compromised.

Actor: `Ermes Gasparini`. Action: `elbow_flexion`. Lane: `inside/hook`. Position: ``.

Enables: `['stop_high_above_pin_line_despite_wrist_compromise']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a108_19

Claim `108`: [03:30](https://www.youtube.com/watch?v=5xm7odwrnZQ&t=210s) Ermes' ultimate tactical goal is to secure a stop and then transition into a flop press.

Actor: `Ermes Gasparini`. Action: `flop_press_transition`. Lane: `unknown`. Position: ``.

Enables: `['Plan_B_to_finish_if_pin_is_not_quick']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a109_20

Claim `109`: [00:28](https://www.youtube.com/watch?v=WqqN3HDvBNk&t=28s) Ermes managed 67kg (147 lbs) on a pronation lift, but his arm angle opened significantly during the attempt.

Actor: `Ermes Gasparini`. Action: `pronation`. Lane: `outside/toproll`. Position: ``.

Enables: `['baseline_pronation_strength_in_training']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a110_21

Claim `110`: [01:15](https://www.youtube.com/watch?v=WqqN3HDvBNk&t=75s) Ermes likely has a stronger elbow flexor than anyone in the world except Levan Saginashvili.

Actor: `Ermes Gasparini`. Action: `elbow_flexion`. Lane: `unknown`. Position: ``.

Enables: `['elite_elbow_flexor_strength']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a111_22

Claim `111`: [01:30](https://www.youtube.com/watch?v=WqqN3HDvBNk&t=90s) Ermes' pronation is weaker than Devon Larratt's and potentially weaker than Vitaly Laletin's or Georgi Tsvetkov's.

Actor: `Ermes Gasparini`. Action: `pronation`. Lane: `unknown`. Position: ``.

Enables: `['relative_pronation_strength_compared_to_others']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a112_23

Claim `112`: [01:45](https://www.youtube.com/watch?v=WqqN3HDvBNk&t=105s) Ermes would outperform Devon Larratt on any lift isolated to the elbow flexors.

Actor: `Ermes Gasparini`. Action: `elbow_flexion`. Lane: `unknown`. Position: ``.

Enables: `['superiority_in_elbow_flexion_vs_devon']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a113_24

Claim `113`: [02:05](https://www.youtube.com/watch?v=WqqN3HDvBNk&t=125s) Ermes has recorded nearly 100kg of back pressure in training.

Actor: `Ermes Gasparini`. Action: `back_pressure`. Lane: `unknown`. Position: ``.

Enables: `['nearly_100kg_back_pressure_in_training']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

### a114_25

Claim `114`: [02:15](https://www.youtube.com/watch?v=WqqN3HDvBNk&t=135s) In their match, Ermes stopped Levan with back pressure but was unable to crack Levan's wrist back.

Actor: `Ermes Gasparini`. Action: `back_pressure`. Lane: `center_table`. Position: ``.

Enables: `['stops_levan_with_back_pressure_but_lacks_wrist_control_to_finish']`
Denies: `[]`
Follow-up: `[]`
Condition: 
Current form usable: `False`. Durable style: `True`. Historical: `True`.
Caveat: 

