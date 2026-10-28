# DiE tháº­t cho cá»•ng F1 â€” ghi chÃº (manifest v1.1)

QuÃ©t: KhÃ¡nh (Kali). RÃ  sá»‘, bá» mÃ£ mÃ u, Ä‘Æ°a lÃªn repo: Tuáº¥n.

## CÃ´ng cá»¥ vÃ  mÃ´i trÆ°á»ng

- Detect It Easy dÃ²ng lá»‡nh `diec` **phiÃªn báº£n 3.21** (`die 3.21`), báº£n portable Linux, cháº¡y qua `diec.sh`.
- Há»‡ Ä‘iá»u hÃ nh: Kali Linux (mÃ¡y cá»§a KhÃ¡nh). **[KhÃ¡nh bá»• sung: phiÃªn báº£n Kali]**
- SHA-256 cá»§a gÃ³i DiE portable Ä‘Ã£ dÃ¹ng: **[KhÃ¡nh bá»• sung: cháº¡y `sha256sum` trÃªn file táº£i vá»]**. (GÃ³i `.deb` Ubuntu 26.04 mÃ  Tuáº¥n cÃ i thá»­ cÃ³ SHA-256 `ef4474d93e00f3644ea680518c43b3a65fe3fb739f6d7eac5d13b82235f339b5`, nhÆ°ng Ä‘Ã³ khÃ´ng pháº£i báº£n dÃ¹ng Ä‘á»ƒ quÃ©t.)
- Lá»‡nh cháº¡y cho tá»«ng máº«u: `diec.sh <Ä‘Æ°á»ng_dáº«n_máº«u>` (quÃ©t máº·c Ä‘á»‹nh, chá»‰ phÃ¢n tÃ­ch tÄ©nh, khÃ´ng thá»±c thi máº«u). Timeout 30 giÃ¢y má»—i máº«u.
- Máº¡ng khi quÃ©t: **[KhÃ¡nh xÃ¡c nháº­n: Ä‘Ã£ táº¯t hay chÆ°a]**
- Script: `experiments/run_die_real.py` (báº£n cá»§a KhÃ¡nh; Tuáº¥n chá»‰ thÃªm Ä‘oáº¡n bá» mÃ£ mÃ u ANSI khá»i output). Máº«u Ä‘Æ°á»£c khá»›p vá»›i manifest báº±ng cÃ¡ch **tá»± tÃ­nh SHA-256 tá»«ng file** (tÃªn file á»Ÿ G1/G3 khÃ´ng pháº£i SHA-256).
- KhÃ´ng sá»­a `manifest_v1.1.csv` vÃ  `dataset_v1.1.csv`.

## CÃ¡ch quy Ä‘á»•i output cá»§a DiE sang nhÃ£n `die_result_real`

- CÃ³ dÃ²ng `Protector: â€¦` â†’ **protected**
- KhÃ´ng cÃ³ Protector nhÆ°ng cÃ³ dÃ²ng `Packer: â€¦` â†’ **packed**
- Output rá»—ng, hoáº·c dÃ²ng Ä‘áº§u cÃ³ chá»¯ "unknown" â†’ **unknown**
- CÃ²n láº¡i â†’ **clean** (DiE khÃ´ng tháº¥y packer/protector)
- Trong 596 máº«u khÃ´ng cÃ³ máº«u nÃ o vá»«a cÃ³ Packer vá»«a cÃ³ Protector, nÃªn thá»© tá»± Æ°u tiÃªn trÃªn khÃ´ng áº£nh hÆ°á»Ÿng káº¿t quáº£.
- `die_detect`: dÃ²ng Packer/Protector Ä‘áº§u tiÃªn (Ä‘Ã£ bá» mÃ£ mÃ u). `die_raw`: toÃ n bá»™ output, cÃ¡c dÃ²ng ná»‘i báº±ng " | " (Ä‘Ã£ bá» mÃ£ mÃ u ANSI, ná»™i dung giá»¯ nguyÃªn).

## Sá»‘ lÆ°á»£ng theo nhÃ³m (596/596 máº«u, thiáº¿u 0)

| group | clean | packed | protected | unknown |
|---|---|---|---|---|
| G0 | 110 | 0 | 12 | 0 |
| G1 | 0 | 156 | 0 | 0 |
| G2 | 158 | 2 | 5 | 0 |
| G3 | 0 | 153 | 0 | 0 |

Tá»•ng theo nhÃ³m: G0 122, G1 156, G2 165, G3 153.

## DiE phÃ¡t hiá»‡n gÃ¬

| group | DiE phÃ¡t hiá»‡n | sá»‘ máº«u |
|---|---|---|
| G0 | Protector: .NET Reactor(6.X)[Control Flow, Anti-ILDASM] | 11 |
| G0 | Protector: .NET Reactor(6.X)[Control Flow] | 1 |
| G1 | Packer: MPRESS(2.19) | 117 |
| G1 | Packer: UPX(4.24)[NRV, brute] | 39 |
| G2 | Packer: UPX(3.95)[NRV, brute] | 1 |
| G2 | Packer: UPX(4.24)[NRV, brute] | 1 |
| G2 | Protector: .NET Reactor(6.X)[Control Flow, Anti-ILDASM] | 4 |
| G2 | Protector: PELock(2.X) | 1 |
| G3 | Packer: MPRESS(2.01-2.12)[modified] | 1 |
| G3 | Packer: MPRESS(2.19) | 152 |

## Quan sÃ¡t

- **G1 vÃ  G3 (Ä‘Ã£ Ä‘Ã³ng gÃ³i báº±ng UPX/MPRESS): DiE nháº­n ra 309/309 máº«u lÃ  `packed`** (G1: UPX 39/39, MPRESS 117/117; G3: MPRESS 153/153, trong Ä‘Ã³ 1 máº«u DiE ghi "MPRESS(2.01-2.12)[modified]").
- **G0 (AgentTesla sáº¡ch): 0 máº«u `packed`, nhÆ°ng 12/122 máº«u `protected`** (cáº£ 12 Ä‘á»u lÃ  .NET Reactor 6.X, má»™t cÃ´ng cá»¥ lÃ m rá»‘i .NET, khÃ´ng pháº£i packer). Náº¿u F1-DiE tÃ­nh cáº£ `protected` lÃ  "Ä‘Ã£ Ä‘Ã³ng gÃ³i" thÃ¬ 12 máº«u G0 nÃ y bá»‹ bÃ¡o nháº§m.
- **Bonus G2 (há» khÃ¡c, chÆ°a Ä‘Ã³ng gÃ³i thÃªm): DiE nháº­n 2/165 lÃ  `packed`** (Ä‘á»u UPX: 3.95 vÃ  4.24) **vÃ  5/165 lÃ  `protected`** (4 .NET Reactor, 1 PELock).
- 4 máº«u G2 cÃ³ output "Unknown: Unknown" (DiE khÃ´ng khá»›p chá»¯ kÃ½ nÃ o) Ä‘ang Ä‘Æ°á»£c gÃ¡n `clean` theo quy táº¯c trÃªn. GÃ¡n `unknown` hay `clean` khÃ´ng Ä‘á»•i káº¿t quáº£ cá»•ng, vÃ¬ cáº£ hai Ä‘á»u khÃ´ng bá»‹ F1 cháº·n.
- Cá»™t `die_result` Ä‘Ã£ gÃ¡n sáºµn trong manifest chÆ°a Ä‘Æ°á»£c so sÃ¡nh trong file nÃ y (khÃ´ng cÃ³ manifest á»Ÿ mÃ¡y rÃ  sá»‘). Äá»©c hoáº·c KhÃ¡nh Ä‘á»‘i chiáº¿u khi cháº¡y lÆ°á»›i.

## CÃ¡ch dÃ¹ng trong lÆ°á»›i F1-DiE

- Äá»c cá»™t `die_result_real`, ná»‘i theo `sha256`.
- Gá»£i Ã½ cháº¡y hai biáº¿n thá»ƒ: **F1-DiE = chá»‰ `packed`** (chÃ­nh) vÃ  **F1-DiE+protected = `packed` hoáº·c `protected`** (Ä‘á»™ nháº¡y).

## ToÃ n váº¹n file

- File KhÃ¡nh gá»­i (cÃ²n mÃ£ mÃ u): SHA-256 `87b0b7a4480c73b0914bacb26ec50f5c5878ab98a8985c467563e576370084d1`
- `results/die_real_v1.1.csv` trong repo (Ä‘Ã£ bá» mÃ£ mÃ u): SHA-256 `27f8ec36553dd2994f1d55d2400d86f6be390025a7f85d73ca9771d59d101481`
- Cá»™t `sha256`, `group` vÃ  `die_result_real` giá»‘ng há»‡t file gá»‘c.

