"""Curated, offline-first learning content for four separate video modes.

Each item has a stable ID so completion history is independent per mode and
can safely survive wording or spelling display changes.
"""
from __future__ import annotations

import re
from .wordbank import WORDBANK

# level, category, word, image query, Bengali meaning, simple example
_OBJECTS = [
("A1","home","bottle","water bottle on a table","বোতল","This is my water bottle."),
("A1","home","cup","drinking cup","কাপ","I drink tea from this cup."),
("A1","home","glass","drinking glass","গ্লাস","Please give me a glass of water."),
("A1","home","plate","dinner plate","প্লেট","Put the rice on the plate."),
("A1","home","bowl","kitchen bowl","বাটি","The soup is in the bowl."),
("A1","home","spoon","metal spoon","চামচ","Use a spoon to eat the soup."),
("A1","home","fork","dinner fork","কাঁটা চামচ","I eat with a fork."),
("A1","home","knife","kitchen knife","ছুরি","Be careful with the knife."),
("A1","home","chair","simple chair","চেয়ার","Please sit on the chair."),
("A1","home","table","wooden table","টেবিল","The book is on the table."),
("A1","home","bed","simple bed","বিছানা","I sleep in my bed."),
("A1","home","pillow","bed pillow","বালিশ","My pillow is soft."),
("A1","home","blanket","folded blanket","কম্বল","This blanket is warm."),
("A1","home","towel","bath towel","তোয়ালে","Dry your hands with a towel."),
("A1","home","soap","bar of soap","সাবান","Wash your hands with soap."),
("A1","home","mirror","bathroom mirror","আয়না","Look in the mirror."),
("A1","home","comb","hair comb","চিরুনি","I use a comb every morning."),
("A1","home","toothbrush","toothbrush","দাঁত মাজার ব্রাশ","My toothbrush is blue."),
("A1","home","bucket","plastic water bucket","বালতি","Fill the bucket with water."),
("A1","home","broom","house broom","ঝাড়ু","The broom is behind the door."),
("A1","home","key","house key","চাবি","I cannot find my key."),
("A1","home","lock","door lock","তালা","The lock is on the door."),
("A1","home","door","wooden house door","দরজা","Please close the door."),
("A1","home","window","open house window","জানালা","Open the window, please."),
("A1","school","book","open book","বই","I read a book every day."),
("A1","school","notebook","school notebook","খাতা","Write your name in the notebook."),
("A1","school","pen","ballpoint pen","কলম","This pen writes well."),
("A1","school","pencil","wooden pencil","পেন্সিল","Use a pencil to draw."),
("A1","school","eraser","rubber eraser","রাবার","I need an eraser."),
("A1","school","ruler","school ruler","স্কেল","Draw a straight line with a ruler."),
("A1","school","backpack","school backpack","ব্যাকপ্যাক","My backpack is heavy."),
("A1","school","desk","student desk","পড়ার ডেস্ক","My desk is near the window."),
("A1","personal","phone","smartphone","ফোন","My phone is charging."),
("A1","personal","wallet","leather wallet","মানিব্যাগ","My wallet is in my bag."),
("A1","personal","watch","wristwatch","ঘড়ি","My watch is five minutes fast."),
("A1","personal","eyeglasses","pair of eyeglasses","চশমা","I wear eyeglasses to read."),
("A1","clothing","shirt","plain shirt","শার্ট","He is wearing a white shirt."),
("A1","clothing","trousers","pair of trousers","প্যান্ট","These trousers are too long."),
("A1","clothing","shoes","pair of shoes","জুতা","Take off your shoes."),
("A1","clothing","socks","pair of socks","মোজা","I need clean socks."),
("A1","clothing","jacket","casual jacket","জ্যাকেট","Wear a jacket outside."),
("A1","travel","umbrella","open umbrella","ছাতা","Take an umbrella. It may rain."),
("A1","travel","bus","city bus","বাস","The bus is late."),
("A1","travel","bicycle","bicycle","সাইকেল","I go to school by bicycle."),
("A1","kitchen","kettle","electric kettle","কেটলি","The kettle is full of water."),
("A1","kitchen","pan","frying pan","ফ্রাইং প্যান","Heat the oil in the pan."),
("A1","kitchen","pot","cooking pot","হাঁড়ি","The rice is in the pot."),
("A1","kitchen","fridge","refrigerator","ফ্রিজ","Keep the milk in the fridge."),
("A1","kitchen","stove","gas cooking stove","চুলা","The stove is hot."),
("A1","kitchen","spatula","kitchen spatula","খুন্তি","Use a spatula to turn the egg."),
("A1","kitchen","whisk","wire kitchen whisk","ডিম ফেটানোর হুইস্ক","Use a whisk to mix the eggs."),
("A2","home","curtain","window curtain","পর্দা","Please open the curtains."),
("A2","home","hanger","clothes hanger","কাপড়ের হ্যাঙ্গার","Hang your shirt on a hanger."),
("A2","home","laundry basket","laundry basket","কাপড় রাখার ঝুড়ি","Put the dirty clothes in the laundry basket."),
("A2","home","doormat","door mat","পাপোশ","Wipe your feet on the doormat."),
("A2","home","extension cord","electrical extension cord","এক্সটেনশন কর্ড","The extension cord is under the desk."),
("A2","personal","charger","phone charger","চার্জার","I forgot my phone charger."),
("A2","personal","headphones","over ear headphones","হেডফোন","I use headphones on the bus."),
("A2","personal","keyboard","computer keyboard","কিবোর্ড","The keyboard is next to the mouse."),
("A2","personal","laptop","open laptop computer","ল্যাপটপ","I use my laptop for work."),
("A2","personal","flashlight","handheld flashlight","টর্চলাইট","Use a flashlight in the dark."),
("A2","school","stapler","office stapler","স্ট্যাপলার","Use a stapler to join the pages."),
("A2","school","scissors","open pair of scissors","কাঁচি","Cut the paper with scissors."),
("A2","school","calculator","handheld calculator","ক্যালকুলেটর","Use a calculator for the sum."),
("A2","kitchen","cutting board","wooden cutting board","কাটিং বোর্ড","Put the vegetables on the cutting board."),
("A2","kitchen","colander","kitchen colander straining pasta","ঝাঁঝরি","Drain the rice in a colander."),
("A2","kitchen","ladle","soup ladle","হাতা","Use a ladle to serve the soup."),
("A2","kitchen","grater","kitchen cheese grater","কুরুনি","Use a grater to grate the carrot."),
("A2","kitchen","peeler","vegetable peeler","খোসা ছাড়ানোর যন্ত্র","This peeler removes potato skin."),
("A2","tools","screwdriver","screwdriver hand tool","স্ক্রু ড্রাইভার","I need a screwdriver to fix the handle."),
("A2","tools","hammer","claw hammer","হাতুড়ি","Use a hammer to drive the nail."),
("A2","tools","wrench","adjustable wrench tool","রেঞ্চ","The wrench is in the toolbox."),
("A2","tools","pliers","hand pliers tool","প্লায়ার্স","Hold the wire with pliers."),
("A2","tools","tape measure","measuring tape tool","মাপার ফিতা","Use a tape measure to check the length."),
("A2","travel","helmet","bicycle safety helmet","হেলমেট","Always wear a helmet when cycling."),
("A2","travel","suitcase","travel suitcase","স্যুটকেস","My suitcase is ready for the trip."),
("A2","travel","rickshaw","cycle rickshaw Bangladesh","রিকশা","We took a rickshaw to the market."),
("A2","health","thermometer","digital thermometer","থার্মোমিটার","The thermometer shows the temperature."),
("A2","health","bandage","medical bandage roll","ব্যান্ডেজ","Put a bandage on the cut."),
("A2","health","first aid kit","first aid kit open","প্রাথমিক চিকিৎসার বাক্স","Keep a first aid kit at home."),
("A1","animals","cat","house cat sitting on a sofa","বিড়াল","The cat is sleeping."),
("A1","animals","dog","friendly pet dog","কুকুর","The dog is playing outside."),
("A1","animals","cow","cow standing in a green field","গরু","The cow eats grass."),
("A1","animals","horse","brown horse standing","ঘোড়া","The horse runs fast."),
("A1","animals","goat","domestic goat","ছাগল","The goat is eating leaves."),
("A1","animals","sheep","sheep in a pasture","ভেড়া","The sheep has thick wool."),
("A1","animals","chicken","hen and chicken in a farmyard","মুরগি","The chicken lays eggs."),
("A1","animals","duck","duck swimming in a pond","হাঁস","The duck is swimming."),
("A1","animals","rabbit","white rabbit sitting on grass","খরগোশ","The rabbit has long ears."),
("A1","animals","fish","goldfish swimming in a tank","মাছ","The fish swims in water."),
("A2","birds","parrot","green parrot perched on a branch","টিয়া পাখি","The parrot can copy sounds."),
("A2","birds","owl","owl sitting on a tree branch","পেঁচা","An owl can see at night."),
("A2","birds","eagle","eagle flying over mountains","ঈগল","The eagle has sharp eyesight."),
("A2","birds","peacock","peacock displaying its colorful feathers","ময়ূর","The peacock has a beautiful tail."),
("A2","birds","penguin","penguin standing on ice","পেঙ্গুইন","Penguins cannot fly."),
("A2","birds","swan","white swan on a lake","রাজহাঁস","The swan is swimming on the lake."),
("A2","birds","pigeon","grey pigeon standing on a pavement","কবুতর","A pigeon is sitting on the roof."),
("A2","birds","flamingo","pink flamingo standing in shallow water","ফ্লেমিঙ্গো","The flamingo has long legs."),
("A2","animals","dolphin","dolphin jumping out of the sea","ডলফিন","The dolphin is swimming near the boat."),
("A2","animals","elephant","elephant walking in grassland","হাতি","The elephant has a long trunk."),
("A2","animals","giraffe","giraffe standing beside a tree","জিরাফ","The giraffe has a long neck."),
("A2","animals","zebra","zebra standing on grassland","জেব্রা","A zebra has black and white stripes."),
("A2","animals","turtle","turtle on a rock near water","কচ্ছপ","The turtle moves slowly."),
("A2","animals","frog","green frog sitting on a leaf","ব্যাঙ","The frog can jump."),
("A2","animals","monkey","monkey sitting on a tree","বানর","The monkey is climbing a tree."),
("A1","food","apple","red apple on a table","আপেল","I eat an apple every day."),
("A1","food","banana","ripe yellow bananas","কলা","A banana is easy to carry."),
("A1","food","orange","fresh orange fruit","কমলা","Would you like an orange?"),
("A1","food","mango","ripe mango fruit","আম","Mango is a popular fruit."),
("A1","food","grapes","bunch of green grapes","আঙুর","These grapes are sweet."),
("A1","food","watermelon","whole and sliced watermelon","তরমুজ","Watermelon contains a lot of water."),
("A1","food","carrot","fresh orange carrots","গাজর","A carrot is crunchy."),
("A1","food","potato","potatoes on a kitchen counter","আলু","We need potatoes for dinner."),
("A1","food","tomato","ripe red tomatoes","টমেটো","The tomato is ripe."),
("A1","food","onion","brown onions on a kitchen counter","পেঁয়াজ","Chop the onion carefully."),
("A1","food","cucumber","fresh cucumber on a cutting board","শসা","I put cucumber in my salad."),
("A1","food","cabbage","green cabbage head","বাঁধাকপি","Cut the cabbage into small pieces."),
("A1","vehicles","car","modern passenger car parked outside","গাড়ি","The car is parked outside."),
("A1","vehicles","train","passenger train at a railway station","ট্রেন","The train arrives at six."),
("A1","vehicles","truck","delivery truck on a road","ট্রাক","The truck carries boxes."),
("A1","vehicles","taxi","yellow taxi on a city street","ট্যাক্সি","We took a taxi to the station."),
("A1","vehicles","airplane","passenger airplane in the sky","বিমান","The airplane is flying above the clouds."),
("A1","vehicles","boat","small wooden boat on a river","নৌকা","The boat is crossing the river."),
("A2","vehicles","ship","large cargo ship at sea","জাহাজ","The ship is leaving the port."),
("A2","vehicles","motorcycle","motorcycle parked on a street","মোটরসাইকেল","He rides a motorcycle to work."),

("B1","science","solar panel","solar panels on a house roof","সোলার প্যানেল","The solar panel collects energy from sunlight."),
("B1","science","wind turbine","wind turbine on an open field","বায়ু বিদ্যুৎ টারবাইন","The wind turbine produces electricity."),
("B1","science","satellite dish","satellite dish mounted on a roof","স্যাটেলাইট ডিশ","The satellite dish receives signals."),
("B1","home","smoke detector","smoke detector attached to a ceiling","ধোঁয়া শনাক্তকারী যন্ত্র","The smoke detector makes a loud sound."),
("B1","health","fire extinguisher","red fire extinguisher mounted on a wall","আগুন নেভানোর যন্ত্র","Keep a fire extinguisher near the kitchen."),
("B1","travel","life jacket","orange life jacket on a boat","লাইফ জ্যাকেট","Wear a life jacket on the boat."),
("B1","home","water filter","home drinking water filter","পানি পরিশোধক ফিল্টার","This water filter makes drinking water cleaner."),
("B1","personal","power bank","portable power bank charging a phone","পাওয়ার ব্যাংক","I carry a power bank when I travel."),
("B1","office","printer","desktop printer on an office desk","প্রিন্টার","The printer is out of paper."),
("B1","office","scanner","flatbed document scanner","স্ক্যানার","Use the scanner to copy this document."),
("B1","office","projector","digital projector in a meeting room","প্রজেক্টর","The teacher uses a projector in class."),
("B1","office","microphone","microphone on a desk stand","মাইক্রোফোন","Speak clearly into the microphone."),
("B1","personal","router","wireless internet router","রাউটার","The router is next to the computer."),
("B1","tools","tripod","camera tripod standing on the floor","ট্রাইপড","Put the camera on the tripod."),
("B1","home","washing machine","front loading washing machine","ওয়াশিং মেশিন","The washing machine is running."),
("B1","home","air conditioner","wall mounted air conditioner","এয়ার কন্ডিশনার","The air conditioner keeps the room cool."),
("B1","home","dishwasher","open dishwasher in a kitchen","ডিশওয়াশার","The dishwasher cleans the plates."),
("B1","tools","water pump","electric water pump","পানির পাম্প","The water pump fills the tank."),
("B1","tools","generator","portable electric generator","জেনারেটর","The generator supplies electricity."),
("B1","travel","traffic cone","orange traffic cone on a road","ট্রাফিক কোন","The worker placed a traffic cone on the road."),
("B1","travel","seat belt","car seat belt buckle","সিট বেল্ট","Always fasten your seat belt."),
("B1","household","recycling bin","colored recycling bin outside a house","পুনর্ব্যবহারের ডাস্টবিন","Put plastic bottles in the recycling bin."),
("B1","tools","extension ladder","folding extension ladder","এক্সটেনশন মই","He used an extension ladder to reach the roof."),
("B1","home","dehumidifier","small home dehumidifier","আর্দ্রতা কমানোর যন্ত্র","The dehumidifier removes moisture from the air."),

]

# Selected, useful items from the old photo-focused bank. The full historical bank
# remains in wordbank.py, but rare species, obsolete objects and look-alike words
# are no longer automatically served as beginner/intermediate lessons.
_LEGACY_OBJECT_ALLOWLIST = {
    "colander", "ladle", "rolling pin", "grater", "peeler", "tongs", "food processor",
    "mixing bowl", "measuring cup", "measuring spoons", "bottle opener", "can opener",
    "pressure cooker", "rice cooker", "garlic press", "salt shaker", "funnel", "sieve",
    "soup tureen", "alarm clock", "bookcase", "dustpan", "hammock", "mailbox",
    "sewing machine", "ironing board", "clothesline", "coat rack", "doormat", "watering can",
    "birdhouse", "birdcage", "lantern", "thermos", "wardrobe", "rocking chair",
    "picture frame", "paperclip", "stapler", "hole punch", "walkie-talkie",
    "pencil sharpener", "filing cabinet", "typewriter", "screwdriver", "wrench", "pliers",
    "tape measure", "hacksaw", "hand drill", "trowel", "spade", "pitchfork", "rake",
    "wheelbarrow", "axe", "crowbar", "padlock", "soldering iron", "paint roller",
    "croissant", "bagel", "baguette", "dumpling", "samosa", "papaya", "ginger root",
    "garlic bulb", "eggplant", "excavator", "forklift", "scooter", "canoe", "kayak",
}

# level, action verb, object, Pixabay search phrase, Bengali meaning, example sentence
_ACTIONS = [
("A1","open","a bottle","person opening a plastic water bottle","খোলা","He is opening a bottle."),
("A1","close","a door","person closing a house door","বন্ধ করা","She is closing the door."),
("A1","drink","water","person drinking a glass of water","পান করা","He is drinking water."),
("A1","eat","an apple","person eating an apple","খাওয়া","She is eating an apple."),
("A1","write","in a notebook","person writing in a notebook","লেখা","He is writing in a notebook."),
("A1","read","a book","person reading an open book","পড়া","She is reading a book."),
("A1","wash","a plate","person washing a plate in a sink","ধোয়া","He is washing a plate."),
("A1","cook","a meal","person cooking food in a kitchen","রান্না করা","She is cooking a meal."),
("A1","run","in a park","person running in a park","দৌড়ানো","He is running in the park."),
("A1","walk","to work","person walking on a footpath","হাঁটা","She is walking to work."),
("A1","sit","on a chair","person sitting on a chair","বসা","He is sitting on a chair."),
("A1","stand","in a room","person standing in a room","দাঁড়ানো","She is standing in the room."),
("A1","sleep","in a bed","person sleeping in a bed","ঘুমানো","The child is sleeping."),
("A1","draw","a picture","person drawing a picture with a pencil","আঁকা","He is drawing a picture."),
("A1","cut","paper with scissors","person cutting paper with scissors","কাটা","She is cutting paper."),
("A1","carry","a bag","person carrying a backpack","বহন করা","He is carrying a bag."),
("A1","push","a shopping cart","person pushing a shopping cart","ধাক্কা দেওয়া","She is pushing a cart."),
("A1","pull","a suitcase","person pulling a suitcase","টেনে নেওয়া","He is pulling a suitcase."),
("A1","throw","a ball","person throwing a ball","ছোড়া","She is throwing a ball."),
("A1","catch","a ball","person catching a ball","ধরা","He is catching a ball."),
("A2","twist","a bottle cap","close up person twisting a water bottle cap","পেঁচিয়ে খোলা বা বন্ধ করা","He is twisting the bottle cap."),
("A2","pour","water into a glass","person pouring water from a jug into a glass","ঢালা","She is pouring water into a glass."),
("A2","stir","soup in a pot","person stirring soup in a cooking pot","নাড়া","He is stirring the soup."),
("A2","peel","a potato","person peeling a potato with a peeler","খোসা ছাড়ানো","She is peeling a potato."),
("A2","grate","a carrot","person grating a carrot in a kitchen","কুরানো","He is grating a carrot."),
("A2","fold","a shirt","person folding a clean shirt","ভাঁজ করা","She is folding a shirt."),
("A2","hang","clothes on a line","person hanging clothes on a washing line","ঝুলিয়ে দেওয়া","He is hanging clothes."),
("A2","sweep","the floor","person sweeping a floor with a broom","ঝাড়ু দেওয়া","She is sweeping the floor."),
("A2","mop","the floor","person mopping a kitchen floor","মোছা","He is mopping the floor."),
("A2","brush","his teeth","person brushing teeth in a bathroom mirror","ব্রাশ করা","He is brushing his teeth."),
("A2","water","the plants","person watering green plants with a watering can","পানি দেওয়া","She is watering the plants."),
("A2","repair","a bicycle","person repairing a bicycle wheel with tools","মেরামত করা","He is repairing a bicycle."),
("A2","tighten","a screw","person tightening a screw with a screwdriver","শক্ত করে আটকানো","She is tightening a screw."),
("A2","unlock","a door","person unlocking a front door with a key","তালা খোলা","He is unlocking the door."),
("A2","measure","a table","person measuring a wooden table with a tape measure","মাপা","She is measuring the table."),
("A2","borrow","a book","student borrowing a book from another student","ধার নেওয়া","He is borrowing a book."),
("B1","compare","two products","person comparing two products in a shop","তুলনা করা","She is comparing two products."),
("B1","explain","a chart","teacher explaining a chart to students","ব্যাখ্যা করা","He is explaining the chart."),
("B1","assemble","a chair","person assembling a flat pack chair","জোড়া লাগানো","She is assembling a chair."),
("B1","replace","a light bulb","person replacing a household light bulb","বদলে দেওয়া","He is replacing the light bulb."),
("B1","organize","a bookshelf","person organizing books on a shelf","গোছানো","She is organizing the books."),
("A1","brush","teeth","person brushing teeth in a bathroom mirror","দাঁত মাজা","He is brushing his teeth."),
("A1","comb","hair","person combing hair in front of a mirror","চুল আঁচড়ানো","She is combing her hair."),
("A1","ride","a bicycle","person riding a bicycle on a street","সাইকেল চালানো","He is riding a bicycle."),
("A1","turn on","a light","person turning on a room light switch","চালু করা","She is turning on the light."),
("A1","turn off","a tap","person turning off a water tap","বন্ধ করা","He is turning off the tap."),
("A1","put on","a jacket","person putting on a jacket","পরে নেওয়া","She is putting on a jacket."),
("A1","take off","shoes","person taking off shoes at a doorway","খুলে ফেলা","He is taking off his shoes."),
("A1","pick up","a box","person picking up a cardboard box","তুলে নেওয়া","She is picking up a box."),
("A2","tie","shoelaces","person tying their shoelaces","ফিতা বাঁধা","He is tying his shoelaces."),
("A2","pack","a suitcase","person packing clothes into a suitcase","গুছিয়ে ভরা","She is packing a suitcase."),
("A2","fill","a bottle","person filling a reusable water bottle","ভরে দেওয়া","He is filling a bottle with water."),
("A2","empty","a box","person emptying a cardboard box onto a table","খালি করা","She is emptying a box."),
("A2","wipe","the table","person wiping a table with a cloth","মুছে ফেলা","He is wiping the table."),
("A2","plant","a seed","person planting a seed in soil","বীজ রোপণ করা","She is planting a seed."),
("A2","unlock","a phone","person unlocking a smartphone with a fingerprint","ফোনের লক খোলা","He is unlocking his phone."),
("A2","charge","a phone","person plugging a phone into a charger","চার্জ দেওয়া","She is charging her phone."),
("A2","fasten","a seat belt","person fastening a seat belt in a car","বেল্ট আটকানো","He is fastening his seat belt."),
("B1","install","a phone app","person installing an app on a smartphone","ইনস্টল করা","She is installing a phone app."),
("B1","present","a report","person presenting a report to coworkers","উপস্থাপন করা","He is presenting a report."),
("B1","deliver","a parcel","delivery worker delivering a parcel to a door","পৌঁছে দেওয়া","She is delivering a parcel."),
("B1","connect","a cable","person connecting a cable to a computer","সংযোগ করা","He is connecting a cable."),
("B1","adjust","a mirror","person adjusting a side mirror in a car","ঠিক করে নেওয়া","She is adjusting the mirror."),
("B1","refill","a container","person refilling a water container","আবার ভরে দেওয়া","He is refilling a container."),
]

# level, word, English definition, query, Bengali meaning, example
_VOCAB = [
("A1","help","to make something easier for someone","person helping a friend carry boxes","সাহায্য করা","Can you help me with this bag?"),
("A1","need","to require something","person looking for a needed item at home","প্রয়োজন হওয়া","I need a glass of water."),
("A1","want","to wish to have or do something","person choosing something in a shop","চাওয়া","I want to learn English."),
("A1","begin","to start doing something","student beginning to write in a notebook","শুরু করা","The class begins at nine."),
("A1","finish","to complete something","person finishing a school assignment","শেষ করা","I finish work at five."),
("A1","choose","to decide which one you want","person choosing fruit at a market","বেছে নেওয়া","Choose the blue shirt."),
("A1","bring","to take something with you to a place","person bringing a bag into a room","নিয়ে আসা","Please bring your notebook."),
("A1","send","to make something go to another person","person sending a message on a phone","পাঠানো","I will send you the photo."),
("A2","borrow","to use something and return it later","student borrowing a book","ধার নেওয়া","May I borrow your pen?"),
("A2","return","to give something back","person returning a book to a library","ফেরত দেওয়া","Please return the book tomorrow."),
("A2","prepare","to make something ready","person preparing ingredients for cooking","প্রস্তুত করা","I prepare breakfast every morning."),
("A2","improve","to become better","student studying and practicing English","উন্নতি করা","I want to improve my English."),
("A2","explain","to make something clear by giving details","teacher explaining a lesson to a student","ব্যাখ্যা করা","Can you explain this word?"),
("A2","repair","to fix something that is broken","person repairing a bicycle","মেরামত করা","My father can repair the fan."),
("A2","invite","to ask someone to come somewhere","person inviting a friend to a birthday party","আমন্ত্রণ জানানো","I will invite my friends."),
("A2","decide","to choose after thinking","person making a choice between two options","সিদ্ধান্ত নেওয়া","I need time to decide."),
("A2","avoid","to stay away from something","person avoiding a wet slippery floor","এড়িয়ে চলা","Try to avoid too much sugar."),
("A2","protect","to keep someone or something safe","person protecting their head with a helmet","রক্ষা করা","Sunscreen helps protect your skin."),
("A2","share","to give part of something to others","friends sharing food at a table","ভাগ করে নেওয়া","We share our ideas."),
("A2","save","to keep something for later or prevent loss","person putting money into a savings jar","জমানো বা বাঁচানো","I save a little money every month."),
("B1","achieve","to succeed in doing something after effort","student celebrating an achieved goal","অর্জন করা","You can achieve your goals with practice."),
("B1","increase","to become or make something larger in amount","worker increasing the amount on a chart","বৃদ্ধি করা","We need to increase our sales."),
("B1","reduce","to make something smaller in amount or size","person reducing waste by sorting items","কমানো","We should reduce plastic waste."),
("B1","suggest","to offer an idea for someone to consider","two coworkers discussing an idea","পরামর্শ দেওয়া","I suggest taking a short break."),
("B1","notice","to see or become aware of something","person noticing a small detail on a page","লক্ষ্য করা","Did you notice the change?"),
("B1","expect","to think that something will happen","person waiting for a delivery","আশা করা","I expect the bus to arrive soon."),
("B1","manage","to succeed in doing or controlling something","person managing a busy work schedule","সামলানো","She manages her time well."),
("B1","opportunity","a situation that makes it possible to do something","student receiving a learning opportunity","সুযোগ","This job is a good opportunity."),
("B1","decision","a choice that you make after thinking","person deciding between two options","সিদ্ধান্ত","It was a difficult decision."),
("B1","confident","feeling sure about your ability","person confidently speaking to a group","আত্মবিশ্বাসী","She feels confident when she speaks English."),
("A1","remember","to keep something in your mind","person remembering a note on a calendar","মনে রাখা","Please remember my name."),
("A1","forget","to fail to remember something","person looking for keys they forgot","ভুলে যাওয়া","I sometimes forget my keys."),
("A1","easy","not difficult to do","person solving a simple puzzle","সহজ","This exercise is easy."),
("A1","difficult","not easy to do","student working on a difficult question","কঠিন","This question is difficult."),
("A1","busy","having a lot to do","person working at a busy desk","ব্যস্ত","I am busy right now."),
("A1","careful","giving attention to avoid danger or mistakes","person carefully crossing a street","সতর্ক","Be careful on the road."),
("A1","important","having great value or meaning","student reading an important message","গুরুত্বপূর্ণ","Sleep is important for your health."),
("A1","different","not the same","two people choosing different colored shirts","ভিন্ন","We have different ideas."),
("A1","enough","as much or as many as needed","person measuring enough rice for a meal","যথেষ্ট","We have enough time."),
("A1","safe","not in danger or likely to be harmed","person wearing a safety helmet","নিরাপদ","Keep your phone safe."),
("A2","available","ready to be used or obtained","customer checking whether a product is available","পাওয়া যাচ্ছে","Is this room available?"),
("A2","continue","to keep doing something","person continuing to study at a desk","চালিয়ে যাওয়া","Please continue your work."),
("A2","depend","to need or be decided by something else","person checking a weather forecast before a trip","নির্ভর করা","It depends on the weather."),
("A2","describe","to say what someone or something is like","student describing a picture to a teacher","বর্ণনা করা","Can you describe the picture?"),
("A2","discover","to find something for the first time","person discovering a new place on a map","আবিষ্কার করা","We discovered a quiet place."),
("A2","prefer","to like one thing more than another","customer choosing tea instead of coffee","বেশি পছন্দ করা","I prefer tea to coffee."),
("A2","possible","able to happen or be done","person checking possible travel dates on a calendar","সম্ভব","Is it possible to meet today?"),
("A2","common","happening often or found in many places","teacher showing common English words on a board","সাধারণ বা প্রচলিত","This is a common mistake."),
("B1","responsible","having a duty to deal with something","person responsible for a team task","দায়িত্বশীল","I am responsible for this project."),
]

# level, target keyword, phrase, English function, image query, Bengali meaning, example/context
_PHRASES = [
("A1","hello","Hello! How are you?","greet someone","two friends greeting each other","হ্যালো! আপনি কেমন আছেন?","Hello! How are you today?"),
("A1","please","Could you help me, please?","ask for help politely","person politely asking another person for help","দয়া করে আমাকে সাহায্য করবেন?","Could you help me, please?"),
("A1","thanks","Thank you very much.","show gratitude","person thanking a shop assistant","আপনাকে অনেক ধন্যবাদ।","Thank you very much for your help."),
("A1","sorry","I'm sorry I'm late.","apologize","person apologizing to a friend","দেরি হওয়ায় আমি দুঃখিত।","I'm sorry I'm late."),
("A1","repeat","Could you say that again?","ask someone to repeat","student asking a teacher a question","আপনি কি আবার বলবেন?","Could you say that again, please?"),
("A1","understand","I don't understand.","say you do not understand","student looking confused during a lesson","আমি বুঝতে পারছি না।","Sorry, I don't understand."),
("A1","name","What is your name?","ask someone's name","two people introducing themselves","আপনার নাম কী?","Hi, what is your name?"),
("A1","direction","Where is the bus stop?","ask for directions","person asking for directions on a street","বাস স্টপ কোথায়?","Excuse me, where is the bus stop?"),
("A2","price","How much does this cost?","ask the price","customer asking a shopkeeper about a product price","এটার দাম কত?","How much does this bag cost?"),
("A2","available","Is this seat taken?","ask if a seat is free","person asking about an empty seat on a bus","এই আসনটি কি খালি?","Excuse me, is this seat taken?"),
("A2","permission","May I come in?","ask permission","student asking permission at a classroom door","আমি কি ভেতরে আসতে পারি?","May I come in, please?"),
("A2","wait","Could you wait a moment?","ask someone to wait","person asking another person to wait","আপনি কি একটু অপেক্ষা করবেন?","Could you wait a moment, please?"),
("A2","clarify","What do you mean?","ask for clarification","two coworkers clarifying a point in conversation","আপনি কী বোঝাতে চাচ্ছেন?","What do you mean by that?"),
("A2","recommend","What do you recommend?","ask for a recommendation","customer asking a cafe worker for a recommendation","আপনি কী পরামর্শ দেবেন?","What do you recommend here?"),
("A2","appointment","Can we meet tomorrow?","suggest a meeting","two people arranging a meeting","আমরা কি আগামীকাল দেখা করতে পারি?","Can we meet tomorrow afternoon?"),
("A2","repeat","Could you speak more slowly?","ask someone to speak slowly","student listening carefully to a speaker","আপনি কি একটু ধীরে বলবেন?","Could you speak more slowly, please?"),
("B1","opinion","What do you think about this idea?","ask for an opinion","coworkers discussing an idea at a meeting","এই ধারণা সম্পর্কে আপনার মত কী?","What do you think about this idea?"),
("B1","agree","I agree with your point.","agree politely","two coworkers agreeing during a discussion","আমি আপনার কথার সঙ্গে একমত।","I agree with your point."),
("B1","disagree","I see your point, but I disagree.","disagree politely","two people having a respectful discussion","আপনার কথা বুঝছি, তবে আমি একমত নই।","I see your point, but I disagree."),
("B1","clarify","Could you clarify that point?","request a clearer explanation","person asking a colleague to clarify a chart","আপনি কি বিষয়টি পরিষ্কার করবেন?","Could you clarify that point?"),
("B1","reschedule","Could we reschedule the meeting?","change a meeting time","two coworkers changing a calendar appointment","আমরা কি মিটিংয়ের সময় বদলাতে পারি?","Could we reschedule the meeting for Friday?"),
("B1","follow up","I'm following up on my message.","politely ask for an update","person checking a work email on laptop","আমার আগের বার্তার বিষয়ে আবার যোগাযোগ করছি।","I'm following up on my message from Monday."),
("A1","goodbye","See you later!","say goodbye","two friends saying goodbye to each other","আবার দেখা হবে","See you later at school."),
("A1","excuse me","Excuse me, where is the restroom?","get someone's attention politely","person asking a worker for directions","মাফ করবেন","Excuse me, can you help me?"),
("A1","I don't know","I don't know the answer.","say you do not know","student unsure while answering a question","আমি জানি না","I don't know, but I can find out."),
("A1","no problem","No problem at all.","respond to thanks or an apology","two people talking after one says thank you","কোনো সমস্যা নেই","No problem, happy to help."),
("A1","I'm hungry","I'm hungry.","say you need food","person choosing food at a kitchen table","আমার ক্ষুধা পেয়েছে","I'm hungry. Let's eat."),
("A1","I'm tired","I'm tired.","say you need rest","person resting after a long day","আমি ক্লান্ত","I'm tired, so I'm going to bed."),
("A1","time","What time is it?","ask the time","person asking someone for the time","এখন কয়টা বাজে","Excuse me, what time is it?"),
("A1","request","Can I have a glass of water, please?","ask for something politely","person ordering water at a cafe","আমি কি এক গ্লাস পানি পেতে পারি","Can I have a cup of tea, please?"),
("A2","help","Could you give me a hand?","ask for help","two coworkers carrying a box together","আপনি কি আমাকে একটু সাহায্য করবেন","Could you give me a hand with this box?"),
("A2","apology","I didn't mean to do that.","explain an accidental mistake","person apologizing after bumping into someone","আমি ইচ্ছা করে করিনি","I didn't mean to interrupt you."),
("A2","repeat","Would you mind repeating that?","politely ask to hear something again","student asking a teacher to repeat a sentence","আপনি কি আবার বলবেন","Would you mind repeating the last sentence?"),
("A2","late","I'm running a little late.","say you will arrive late","person checking the time while walking to a meeting","আমার একটু দেরি হচ্ছে","I'm running a little late, but I'll be there soon."),
("A2","clarify","Could you explain that another way?","ask for a simpler explanation","student asking a speaker about a diagram","আপনি কি অন্যভাবে বুঝিয়ে বলবেন","Could you explain that another way?"),
("A2","request","Would it be possible to change the time?","make a polite request","person asking a colleague to change a meeting time","সময়টি বদলানো কি সম্ভব হবে","Would it be possible to change the time?"),
("A2","thanks","I really appreciate your help.","show appreciation","person thanking a coworker for helping","আপনার সাহায্যের জন্য কৃতজ্ঞ","I really appreciate your help."),
("A2","cancel","I need to cancel my appointment.","cancel a plan politely","person calling a clinic to cancel an appointment","আমার অ্যাপয়েন্টমেন্ট বাতিল করতে হবে","I need to cancel my appointment."),
("B1","checking in","Just checking in on my previous email.","ask for an update politely","person checking a work email on laptop","আগের ইমেইলের বিষয়ে খোঁজ নিচ্ছি","Just checking in on my previous email."),
("B1","concern","I have a concern about this plan.","express a concern politely","coworkers discussing a project plan","এই পরিকল্পনা নিয়ে আমার একটি উদ্বেগ আছে","I have a concern about this plan."),
("B1","delay","Could you let me know about any delays?","ask about a possible delay","traveler asking an airport worker about a delay","কোনো দেরি হলে আমাকে জানাবেন","Could you let me know about any delays?"),
("B1","point of view","From my point of view, we need more time.","share your point of view","coworkers sharing opinions during a meeting","আমার দৃষ্টিতে আমাদের আরও সময় দরকার","From my point of view, we need more time."),
]


_PLURAL_OBJECTS = {
    "bagpipes", "binoculars", "boots", "castanets", "clothes", "cymbals", "earrings",
    "flip flops", "glasses", "eyeglasses", "gloves", "goggles", "headphones", "ice skates", "jeans",
    "leggings", "maracas", "measuring spoons", "mittens", "pants", "pliers", "roller skates",
    "sandals", "scissors", "shoes", "shorts", "shears", "skis", "socks", "sunglasses",
    "suspenders", "tongs", "trousers", "tweezers", "wellington boots", "chopsticks", "grapes",
}


def object_answer(word: str) -> str:
    """Return a natural spoken identification for singular and plural objects."""
    clean = word.strip()
    if clean.lower() in _PLURAL_OBJECTS:
        return f"These are {clean}."
    lower = clean.lower()
    takes_an = lower[:1] in "aeiou" or lower.startswith(("hour", "honest", "heir", "x-ray"))
    article = "an" if takes_an else "a"
    return f"This is {article} {clean}."

_MODES = {"object": "Object Learning", "action": "Action Learning",
          "vocabulary": "Useful Vocabulary", "phrases": "Everyday Phrases"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def modes() -> dict:
    return dict(_MODES)


def items_for(mode: str, level: str = "mixed", category: str | None = None) -> list[dict]:
    mode = (mode or "object").lower()
    level = (level or "mixed").upper()
    if mode not in _MODES:
        raise ValueError(f"unknown learning mode: {mode}")
    out: list[dict] = []
    def add(item):
        if level not in ("MIXED", "ALL", "") and item["level"] != level:
            return
        if category and item.get("category") != category:
            return
        out.append(item)

    if mode == "object":
        from .words import is_denied, is_valid_shape
        seen = set()
        for lvl, cat, word, query, bn, example in _OBJECTS:
            key = _slug(word)
            if key in seen: continue
            seen.add(key)
            add({"id": f"object_{key}", "type": "object", "mode": mode, "level": lvl,
                 "category": cat, "word": word, "search_query": query,
                 "image_check": word, "question": "What is this called?", "answer": object_answer(word),
                 "slow_text": word, "label": word.title(), "spelling": word,
                 "bengali_meaning": bn, "example": example})
        # Keep the useful middle-difficulty part of the established 1,300-word bank.
        # The more obscure difficulty-3 entries stay archived but are not served by default.
        for word, query, cat, difficulty in WORDBANK:
            key = _slug(word)
            if (key in seen or difficulty != 2 or word not in _LEGACY_OBJECT_ALLOWLIST
                    or is_denied(word) or not is_valid_shape(word)):
                continue
            seen.add(key)
            lvl = "A2"
            add({"id": f"object_{key}", "type": "object", "mode": mode, "level": lvl,
                 "category": cat, "word": word, "search_query": query, "image_check": word,
                 "question": "What is this called?", "answer": object_answer(word), "slow_text": word,
                 "label": word.title(), "spelling": word, "bengali_meaning": "",
                 "example": f"This is a {word}."})
    elif mode == "action":
        for lvl, verb, obj, query, bn, example in _ACTIONS:
            key = _slug(verb + " " + obj)
            # Keep the question and answer independent of the person's gender in the photo.
            neutral_answer = re.sub(r"^(?:He|She|They|The child)\s+is\b", "The person is", example.strip())
            neutral_answer = re.sub(r"\b(?:his|her)\b", "their", neutral_answer, flags=re.I)
            action_description = re.sub(r"^The person is\s+", "", neutral_answer).rstrip(".")
            item = {"id": f"action_{key}", "type": "action", "mode": mode, "level": lvl,
                    "category": "actions", "word": verb + " " + obj, "search_query": query,
                    "image_check": f"a person {action_description}",
                    "question": "What is the person doing?",
                    "answer": neutral_answer, "slow_text": verb, "label": neutral_answer, "spelling": verb,
                    "bengali_meaning": bn, "example": neutral_answer}
            add(item)
    elif mode == "vocabulary":
        for lvl, word, meaning, query, bn, example in _VOCAB:
            key = _slug(word)
            add({"id": f"vocabulary_{key}", "type": "vocabulary", "mode": mode, "level": lvl,
                 "category": "useful_words", "word": word, "search_query": query,
                 "image_check": query, "question": f"What does '{word}' mean?",
                 "answer": f"{word.capitalize()} means {meaning}. Example: {example}",
                 "slow_text": word, "label": word.title(), "spelling": word,
                 "subtitle": meaning.capitalize(), "bengali_meaning": bn, "example": example})
    else:
        for lvl, key_word, phrase, function, query, bn, example in _PHRASES:
            key = _slug(phrase)
            add({"id": f"phrases_{key}", "type": "phrase", "mode": mode, "level": lvl,
                 "category": "daily_communication", "word": phrase, "search_query": query,
                 "image_check": query, "question": f"How can you {function}?",
                 "answer": phrase, "slow_text": phrase, "label": phrase,
                 "spelling": key_word, "subtitle": function.capitalize(),
                 "bengali_meaning": bn, "example": example})
    return out
