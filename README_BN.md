# WordClip Studio

ইংরেজি শেখার ছোট ভিডিও (৯:১৬, TikTok/Shorts/Reels-এর মাপে) বানানোর টুল। চারটি আলাদা Learning Mode আছে:

- **Object Learning:** “What is this called?” → “This is a bottle.”
- **Action Learning:** “What is the person doing?” → “The person is opening a bottle.”
- **Useful Vocabulary:** শব্দের অর্থ ও একটি example sentence।
- **Everyday Phrases:** দৈনন্দিন পরিস্থিতিতে ব্যবহারযোগ্য English phrase।

প্রতিটি ভিডিওতে ৩টি item থাকে। A1, A2, B1 বা Mixed level বেছে নেওয়া যায়। Level-গুলো শেখার সুবিধার জন্য আনুমানিক CEFR target; official exam word-list certification নয়। পুরোনো ১,৩০০-item photo list archive-এ আছে, কিন্তু কেবল বাছাই করা practical object-ই active bank-এ থাকে। সব ভারী কাজ **GitHub Actions** করে; ফোনে শুধু ওয়েব পাতা ব্যবহার করবেন।

## ভিডিও বানানোর নিয়ম

1. Home-এ Learning Mode এবং English level বেছে নিন। Object Learning হলে চাইলে topic-ও বাছতে পারবেন।
2. ডিফল্টে **Manual review বন্ধ** থাকে। সে অবস্থায় Prepare শব্দ ও Pixabay ছবি সংগ্রহ করে, প্রথম ranked ছবি নিজে বেছে নিয়ে Build শুরু করে। শেষ হলে ভিডিও ডাউনলোডের লিংক আসবে।
3. নিজে ছবি বাছতে চাইলে **Manual review** চালু করুন। তখন আগের মতো প্রতিটি শব্দের ছবির candidate দেখাবে; ছবি পছন্দ করে Build চাপবেন।

কোনো mode-এর item সফলভাবে ভিডিওতে ব্যবহৃত হলে সেই mode-এর history-তে ID যোগ হয়; ওই mode-এ item আবার আসবে না। আলাদা mode-এর history আলাদা। Build ব্যর্থ হলে item ব্যবহৃত হিসেবে ধরা হয় না।

## শুরুর আগে যা লাগবে (সব বিনামূল্যে)

| জিনিস | কোথায় পাবেন |
|---|---|
| GitHub অ্যাকাউন্ট | github.com |
| Cloudflare token + Account ID | dash.cloudflare.com (AI: ছবির মিল যাচাই ও arrow placement) |
| Pixabay API key | pixabay.com/api/docs/ (ছবির জন্য) |

Key-গুলো **কখনো চ্যাটে বা কোডে বসাবেন না।** শুধু GitHub-এর Secrets-এ বসবে (SETUP_BN.md-এ দেখানো আছে)।

## কোন ফাইল কী করে

| ফাইল/ফোল্ডার | কাজ |
|---|---|
| `docs/` | ফোনে খোলা ওয়েব পাতা (GitHub Pages থেকে চলে) |
| `engine/` | Python কোড: শব্দ বানানো, ছবি খোঁজা, ভয়েস, ভিডিও রেন্ডার, মান-পরীক্ষা |
| `.github/workflows/` | ৫টি কাজ: Prepare, More images, Build, Check setup, Voice test |
| `github-workflows/` | ওপরের লুকানো `.github/workflows`-এর হুবহু কপি। শুধু ফোন থেকে আপলোডের সুবিধার জন্য, repo-তে তোলার দরকার নেই |
| `config.yaml` | আপনার সেটিং: চ্যানেলের নাম, থিম, ভয়েস, শব্দ-সংখ্যা |
| `assets/fonts/` | ভিডিওর ফন্ট |
| `assets/music/` | ব্যাকগ্রাউন্ড মিউজিক লুপ (মুছলে মিউজিক বন্ধ) |
| `tests/` | স্বয়ংক্রিয় পরীক্ষা (চালাতে না চাইলে আপলোড না করলেও চলবে) |

## ডকুমেন্টের তালিকা

- **SETUP_BN.md**: প্রথমবার চালু করার ধাপে ধাপে নির্দেশ। **এটা দিয়ে শুরু করুন।**
- **TROUBLESHOOTING_BN.md**: সবচেয়ে সম্ভাব্য ১৫টি সমস্যা ও সমাধান।
- **CONFIG_BN.md**: ভয়েস, থিম, চ্যানেলের নাম, শব্দ-সংখ্যা, মিউজিক বদলানোর উপায়।
- **ARCHITECTURE.md**: ডেভেলপারদের জন্য (ইংরেজিতে)।

## জেনে রাখা ভালো

- **ফ্রি সীমা বদলাতে পারে।** Cloudflare, Pixabay আর GitHub Actions-এর ফ্রি সীমা সময়ের সঙ্গে বদলায়। কয়েক সপ্তাহ পরপর একবার দেখে নিন।
- **ভয়েস বিনামূল্যের edge-tts।** মানুষের মতো নিখুঁত নয়। Settings-এর ভয়েস টেস্টে শুনে বেছে নিন।
- **edge-tts অনানুষ্ঠানিক সেবা।** যেকোনো সময় বন্ধ হতে পারে।
- **একসঙ্গে একটি কাজই চলে।** একটার মধ্যে আরেকটা শুরু করলে পরেরটা লাইনে থাকে। লাইনে দুটোর বেশি থাকলে পুরনোটা বাতিল হয়ে যায়। তাই বোতাম একবারই চাপুন।
- **ছবির কৃতজ্ঞতা:** সব ছবি [Pixabay](https://pixabay.com) থেকে। প্রতিটি ভিডিওর Release-এ `credits.json` আর নোটে ফটোগ্রাফারের নাম থাকে। ভিডিও পোস্টের বর্ণনায় “Photos: Pixabay” লিখে দিলে ভালো।
- **নিজের ছবি** দিলে সেটার কপিরাইটের দায়িত্ব আপনার।
- ভিডিওতে কোনো TikTok ওয়াটারমার্ক নেই। নমুনা ভিডিওর ছবি, অডিও বা লোগো কিছুই ব্যবহার হয়নি।

## পোস্টের ক্যাপশন (কপি করুন)

```
Can you answer all 3? 🤔 Comment your score below! 👇
Follow @Lingobits-Official for a new word every day! ✨

#Lingobits #EnglishVocabulary #LearnEnglish #Vocabulary #WordOfTheDay #EnglishQuiz #EnglishChallenge #Shorts #Reels #FYP
```
