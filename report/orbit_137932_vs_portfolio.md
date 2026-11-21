# Santa 2026 attribution report — data/orbit_santa2026_137932.csv

- tool: `santa_attrib v1` (deterministic; no network, stdlib only)
- submission sha256: `659f2bd95d7944adebc1e98e57961be4b282a7e71097b36fb601eef4537ba6e6` (1000 puzzles)
- **total instructions: 137932** | first5 (scored_0001..0005): 950
- helper-chain depth: max 42, mean 19.971, unattributed 0
- techniques: *=46430, +=46042, -=41503, /=3957, diff_squares=97, double=1778, square=3042

| engine | puzzles attributed | instructions attributed |
|---|---|---|
| orbit_portfolio_138054 | 913 | 126742 |
| orbit_rewritten_137932 | 1000 | 137932 |
| unattributed | 0 | 0 |

Depth histogram (depth: puzzles):

1:1 2:4 3:4 4:7 6:1 7:5 8:10 9:17 10:16 11:18 12:21 13:16 14:18 15:24 16:37 17:49 18:76 19:102 20:98 21:105 22:77 23:73 24:47 25:51 26:35 27:20 28:11 29:13 30:13 31:13 32:4 33:4 34:4 35:3 36:1 39:1 42:1

Per-puzzle detail lives in the JSON report of the same run. First 10 puzzles:

| id | instructions | depth | provenance | techniques |
|---|---|---|---|---|
| scored_0001 | 230 | 20 | orbit_portfolio_138054,orbit_rewritten_137932 | *:67, +:97, -:63, /:3, double:3, square:4 |
| scored_0002 | 247 | 21 | orbit_portfolio_138054,orbit_rewritten_137932 | *:88, +:78, -:78, /:3, double:2, square:3 |
| scored_0003 | 213 | 17 | orbit_portfolio_138054,orbit_rewritten_137932 | *:80, +:67, -:62, /:4, diff_squares:1, double:2, square:4 |
| scored_0004 | 212 | 17 | orbit_portfolio_138054,orbit_rewritten_137932 | *:67, +:73, -:70, /:2, double:1, square:6 |
| scored_0005 | 48 | 12 | orbit_portfolio_138054,orbit_rewritten_137932 | *:10, +:28, -:10, double:3, square:1 |
| scored_0006 | 112 | 20 | orbit_portfolio_138054,orbit_rewritten_137932 | *:40, +:42, -:27, /:3, double:1, square:4 |
| scored_0007 | 162 | 35 | orbit_rewritten_137932 | *:57, +:62, -:38, /:5, double:2, square:1 |
| scored_0008 | 111 | 18 | orbit_portfolio_138054,orbit_rewritten_137932 | *:44, +:36, -:23, /:8, double:2, square:2 |
| scored_0009 | 28 | 13 | orbit_portfolio_138054,orbit_rewritten_137932 | *:10, +:11, -:6, /:1, double:4, square:2 |
| scored_0010 | 180 | 21 | orbit_portfolio_138054,orbit_rewritten_137932 | *:43, +:63, -:67, /:7, double:5, square:3 |
