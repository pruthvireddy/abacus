# First countertrend Range XV bar: how many more bars follow?

Study `08_countertrend_bar_continuation`; long-history local run. All displayed rates come from the saved CSV tables in this bundle. This is bar-behavior evidence, not an execution or profitability test.

## Answer for chart watching

After C1 closes, **the next one bar follows 74.4%–76.1% of the time, while the next TWO bars both follow 47.6%–49.5%** across the seven charts when bullish and bearish signals are kept separate. Two more means C2 and C3; C1 is not counted. Among C2 successes, C3 follows 63.7%–65.5%. These are different questions and denominators.

**No positive prior-run-length × session × direction cell passed the frozen screen** (0 of 210 main contrasts; 166 had minimum support). Several high point estimates occur in the thin 16:00–18:00 transition. The strongest supported positive example below has a familywise interval that includes zero. 6 main cells had Bonferroni intervals below their chart/direction/session baselines; these are downward descriptive findings, not a trading rule. Agreement across ES or NQ settings is correlated because the settings transform the same trades.

The practical read is therefore a roughly three-in-four chance of **one** more directional candle, followed by a roughly one-in-two chance of **two** more. An extended prior trend does not produce a stable, reliably higher two-more probability in this snapshot.

## Outcome definitions and sample

A prior trend is an uninterrupted same-direction sequence of completed non-doji bars within one inferred 18:00 New York session. A doji breaks the sequence. C1 is the first completed opposite non-doji bar. C2, C3, and C4 are the next physical bars; a doji fails continuation. A signal is observable at C1's next-bar-start completion proxy. The primary denominator requires C1, C2, and C3 to have strictly later same-session completion proxies. C4 also needs a strict completion for the three-more outcome. Session/export boundary cases and equal-second C1/C2/C3 completions are excluded, not scored as failures.

Windows use C1's completion wall time and half-open boundaries: Asia 18:00–03:00, London/pre-NY 03:00–09:30, NY morning 09:30–12:00, NY afternoon 12:00–16:00, and transition 16:00–18:00. The enhanced clocks already reflect inferred New York daylight-saving time; no second conversion was applied. ATAS timezone configuration was not verified, so these labels depend on that clock interpretation. One observation never crosses an inferred session boundary.

## Chart baselines by direction

Each row is its own same-chart baseline (difference 0 pp). Intervals are 95% session-cluster sandwich intervals. The C2 and both outcomes use the same eligible denominator; dates and events/date apply to both.

| Chart | C1 direction | C2 follows: k/n, rate [95% CI] | C2 and C3 follow: k/n, rate [95% CI] | Dates | Events/date |
|---|---|---:|---:|---:|---:|
| ES 4RXV | bearish | 75.1% (134,754/179,338) [74.9%–75.3%] | 47.9% (85,861/179,338) [47.6%–48.1%] | 1,783 | 100.6 |
| ES 4RXV | bullish | 74.8% (134,146/179,291) [74.6%–75.1%] | 47.8% (85,753/179,291) [47.6%–48.1%] | 1,783 | 100.6 |
| ES 5RXV | bearish | 75.3% (95,265/126,449) [75.1%–75.6%] | 48.3% (61,080/126,449) [48.0%–48.6%] | 1,783 | 70.9 |
| ES 5RXV | bullish | 75.3% (95,074/126,311) [75.0%–75.5%] | 48.3% (61,067/126,311) [48.1%–48.6%] | 1,783 | 70.8 |
| ES 6RXV | bearish | 75.3% (70,649/93,779) [75.1%–75.6%] | 48.5% (45,514/93,779) [48.2%–48.9%] | 1,781 | 52.7 |
| ES 6RXV | bullish | 75.2% (70,494/93,729) [74.9%–75.5%] | 48.7% (45,652/93,729) [48.4%–49.0%] | 1,782 | 52.6 |
| GC 6RXV | bearish | 74.4% (144,769/194,628) [74.0%–74.7%] | 47.7% (92,911/194,628) [47.4%–48.1%] | 1,775 | 109.6 |
| GC 6RXV | bullish | 75.2% (146,786/195,098) [74.9%–75.6%] | 48.6% (94,733/195,098) [48.2%–48.9%] | 1,775 | 109.9 |
| GC 10RXV | bearish | 75.0% (69,514/92,626) [74.7%–75.4%] | 48.5% (44,948/92,626) [48.1%–49.0%] | 1,773 | 52.2 |
| GC 10RXV | bullish | 76.1% (70,669/92,909) [75.7%–76.4%] | 49.5% (46,007/92,909) [49.1%–50.0%] | 1,774 | 52.4 |
| NQ 10RXV | bearish | 74.4% (415,400/557,962) [74.3%–74.6%] | 47.6% (265,713/557,962) [47.4%–47.8%] | 1,783 | 312.9 |
| NQ 10RXV | bullish | 74.5% (415,760/558,125) [74.3%–74.7%] | 47.7% (266,393/558,125) [47.5%–47.9%] | 1,783 | 313.0 |
| NQ 20RXV | bearish | 75.6% (141,130/186,711) [75.4%–75.8%] | 49.5% (92,336/186,711) [49.2%–49.7%] | 1,781 | 104.8 |
| NQ 20RXV | bullish | 75.4% (140,811/186,734) [75.2%–75.6%] | 49.4% (92,288/186,734) [49.2%–49.7%] | 1,783 | 104.7 |

## Other requested outcomes

Conditional C3 uses only primary-eligible C2 successes. Three more uses its own strict C4-complete denominator. Immediate resumption uses the primary denominator. Each cell shows numerator/denominator, rate, 95% interval, and session-date count; events/date and same-chart baseline identity are in the [overall numerical table](tables/overall.csv).

| Chart; C1 | C3 follows given C2 followed | C2–C4 all follow | C2 immediately resumes old trend |
|---|---:|---:|---:|
| ES 4; bearish | 63.7% (85,861/134,754) [63.4%–64.0%]; 1,783 dates | 30.4% (52,489/172,476) [30.2%–30.7%]; 1,783 dates | 24.9% (44,584/179,338) [24.7%–25.1%]; 1,783 dates |
| ES 4; bullish | 63.9% (85,753/134,146) [63.6%–64.2%]; 1,783 dates | 30.6% (52,795/172,411) [30.4%–30.9%]; 1,783 dates | 25.2% (45,145/179,291) [24.9%–25.4%]; 1,783 dates |
| ES 5; bearish | 64.1% (61,080/95,265) [63.8%–64.4%]; 1,781 dates | 31.0% (38,002/122,640) [30.7%–31.3%]; 1,783 dates | 24.7% (31,184/126,449) [24.4%–24.9%]; 1,783 dates |
| ES 5; bullish | 64.2% (61,067/95,074) [63.9%–64.5%]; 1,782 dates | 31.2% (38,161/122,451) [30.9%–31.4%]; 1,783 dates | 24.7% (31,237/126,311) [24.5%–25.0%]; 1,783 dates |
| ES 6; bearish | 64.4% (45,514/70,649) [64.0%–64.8%]; 1,778 dates | 31.4% (28,668/91,379) [31.0%–31.7%]; 1,780 dates | 24.7% (23,130/93,779) [24.4%–24.9%]; 1,781 dates |
| ES 6; bullish | 64.8% (45,652/70,494) [64.4%–65.1%]; 1,782 dates | 31.7% (28,983/91,323) [31.4%–32.1%]; 1,781 dates | 24.8% (23,235/93,729) [24.5%–25.1%]; 1,782 dates |
| GC 6; bearish | 64.2% (92,911/144,769) [63.9%–64.5%]; 1,775 dates | 30.6% (55,208/180,350) [30.3%–30.9%]; 1,775 dates | 25.6% (49,859/194,628) [25.3%–26.0%]; 1,775 dates |
| GC 6; bullish | 64.5% (94,733/146,786) [64.3%–64.8%]; 1,775 dates | 31.4% (56,913/181,014) [31.2%–31.7%]; 1,775 dates | 24.8% (48,312/195,098) [24.4%–25.1%]; 1,775 dates |
| GC 10; bearish | 64.7% (44,948/69,514) [64.3%–65.1%]; 1,773 dates | 31.5% (27,612/87,617) [31.1%–31.9%]; 1,773 dates | 25.0% (23,112/92,626) [24.6%–25.3%]; 1,773 dates |
| GC 10; bullish | 65.1% (46,007/70,669) [64.7%–65.5%]; 1,772 dates | 32.6% (28,667/88,028) [32.2%–32.9%]; 1,773 dates | 23.9% (22,240/92,909) [23.6%–24.3%]; 1,774 dates |
| NQ 10; bearish | 64.0% (265,713/415,400) [63.8%–64.1%]; 1,783 dates | 30.3% (155,111/511,525) [30.2%–30.5%]; 1,783 dates | 25.6% (142,562/557,962) [25.4%–25.7%]; 1,783 dates |
| NQ 10; bullish | 64.1% (266,393/415,760) [63.9%–64.3%]; 1,783 dates | 30.6% (156,902/512,604) [30.4%–30.8%]; 1,783 dates | 25.5% (142,365/558,125) [25.3%–25.7%]; 1,783 dates |
| NQ 20; bearish | 65.4% (92,336/141,130) [65.2%–65.7%]; 1,779 dates | 32.0% (57,695/180,118) [31.8%–32.3%]; 1,781 dates | 24.4% (45,581/186,711) [24.2%–24.6%]; 1,781 dates |
| NQ 20; bullish | 65.5% (92,288/140,811) [65.3%–65.8%]; 1,783 dates | 32.4% (58,397/180,087) [32.2%–32.7%]; 1,783 dates | 24.6% (45,923/186,734) [24.4%–24.8%]; 1,783 dates |

The same table records C2 and C3 dojis separately. Immediate resumption excludes C2 dojis.

## Prior trend length × session lookup

Each cell shows **P(C2 and C3 both follow C1)** with numerator/eligible denominator. Read the matching chart, direction, bin, and window row in [the full lookup](tables/lookup.csv) for P(C2), conditional P(C3), 95% intervals, session-date count, events/date, and matched baseline difference. The 1–2 bin is context; 3–4, 5–7, and 8+ were the main comparisons. The period table gives three chronological blocks. Signals are not pooled across charts.

### ES 4RXV

| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| Bearish; 1-2 | 48.4% (7,224/14,932) | 49.1% (9,369/19,072) | 48.3% (13,377/27,714) | 48.5% (13,703/28,235) | 48.7% (1,053/2,163) |
| Bearish; 3-4 | 46.9% (3,776/8,043) | 47.4% (5,036/10,626) | 48.0% (7,318/15,244) | 46.8% (7,319/15,642) | 46.7% (593/1,270) |
| Bearish; 5-7 | 47.1% (1,978/4,203) | 47.9% (2,756/5,748) | 46.3% (3,696/7,978) | 46.4% (3,804/8,201) | 51.1% (333/652) |
| Bearish; 8+ | 46.7% (716/1,533) | 47.0% (900/1,914) | 46.9% (1,407/2,997) | 47.1% (1,390/2,950) | 51.1% (113/221) |
| Bullish; 1-2 | 48.6% (7,244/14,894) | 49.0% (9,324/19,028) | 48.4% (13,366/27,617) | 48.8% (13,760/28,213) | 50.2% (1,106/2,204) |
| Bullish; 3-4 | 47.3% (3,824/8,088) | 47.8% (5,216/10,915) | 46.8% (7,192/15,373) | 46.2% (7,264/15,727) | 47.0% (610/1,297) |
| Bullish; 5-7 | 46.5% (1,945/4,180) | 47.1% (2,599/5,513) | 46.7% (3,786/8,099) | 46.4% (3,735/8,054) | 52.0% (344/662) |
| Bullish; 8+ | 47.0% (668/1,420) | 47.8% (940/1,965) | 46.0% (1,314/2,855) | 47.4% (1,394/2,943) | 50.0% (122/244) |

### ES 5RXV

| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| Bearish; 1-2 | 49.2% (5,176/10,531) | 48.7% (6,511/13,359) | 48.9% (9,555/19,529) | 49.7% (9,827/19,757) | 51.7% (776/1,501) |
| Bearish; 3-4 | 47.5% (2,716/5,721) | 47.3% (3,576/7,559) | 47.7% (5,127/10,748) | 47.5% (5,206/10,956) | 45.6% (386/846) |
| Bearish; 5-7 | 47.1% (1,419/3,015) | 47.6% (1,889/3,968) | 46.4% (2,672/5,756) | 47.0% (2,766/5,884) | 52.2% (236/452) |
| Bearish; 8+ | 47.3% (476/1,007) | 49.5% (698/1,411) | 45.6% (967/2,122) | 47.1% (1,015/2,157) | 50.6% (86/170) |
| Bullish; 1-2 | 49.7% (5,243/10,547) | 49.8% (6,680/13,414) | 48.8% (9,535/19,528) | 49.4% (9,701/19,645) | 52.3% (772/1,475) |
| Bullish; 3-4 | 47.3% (2,693/5,694) | 47.1% (3,542/7,528) | 47.3% (5,054/10,689) | 46.7% (5,176/11,088) | 47.5% (424/893) |
| Bullish; 5-7 | 47.9% (1,420/2,965) | 46.7% (1,850/3,965) | 47.4% (2,743/5,793) | 47.6% (2,732/5,744) | 48.1% (229/476) |
| Bullish; 8+ | 47.5% (476/1,002) | 50.7% (719/1,418) | 46.3% (974/2,104) | 47.0% (1,025/2,180) | 48.5% (79/163) |

### ES 6RXV

| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| Bearish; 1-2 | 49.1% (3,849/7,841) | 49.8% (4,872/9,787) | 50.2% (7,288/14,511) | 49.7% (7,267/14,616) | 50.0% (522/1,043) |
| Bearish; 3-4 | 47.2% (2,024/4,291) | 47.1% (2,657/5,639) | 47.0% (3,733/7,944) | 48.1% (3,941/8,201) | 48.6% (301/619) |
| Bearish; 5-7 | 46.6% (1,028/2,208) | 48.0% (1,390/2,897) | 45.2% (1,946/4,310) | 47.2% (2,035/4,308) | 52.6% (172/327) |
| Bearish; 8+ | 47.8% (374/783) | 47.9% (526/1,097) | 48.1% (767/1,595) | 46.3% (759/1,641) | 52.1% (63/121) |
| Bullish; 1-2 | 49.7% (3,942/7,933) | 50.0% (4,928/9,860) | 49.6% (7,158/14,426) | 49.8% (7,253/14,558) | 52.5% (555/1,058) |
| Bullish; 3-4 | 48.5% (2,028/4,181) | 47.4% (2,610/5,511) | 47.3% (3,842/8,122) | 47.6% (3,891/8,179) | 47.7% (306/641) |
| Bullish; 5-7 | 48.4% (1,073/2,216) | 47.0% (1,400/2,980) | 47.1% (2,000/4,243) | 46.0% (2,009/4,363) | 51.4% (165/321) |
| Bullish; 8+ | 50.4% (370/734) | 51.5% (547/1,062) | 46.2% (742/1,607) | 48.1% (764/1,590) | 47.9% (69/144) |

### GC 6RXV

| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| Bearish; 1-2 | 47.9% (14,624/30,531) | 48.5% (14,088/29,055) | 48.4% (10,287/21,250) | 48.1% (6,834/14,207) | 49.3% (642/1,301) |
| Bearish; 3-4 | 46.6% (8,123/17,440) | 48.0% (8,114/16,908) | 47.1% (5,994/12,727) | 47.5% (3,982/8,391) | 48.2% (384/796) |
| Bearish; 5-7 | 46.6% (4,454/9,552) | 47.5% (4,444/9,347) | 47.6% (3,258/6,846) | 47.2% (2,103/4,452) | 51.4% (213/414) |
| Bearish; 8+ | 46.2% (1,627/3,525) | 48.4% (1,680/3,469) | 47.2% (1,243/2,633) | 45.3% (726/1,602) | 50.0% (91/182) |
| Bullish; 1-2 | 48.9% (15,424/31,553) | 48.8% (14,451/29,584) | 49.1% (10,744/21,867) | 49.3% (7,150/14,491) | 51.1% (685/1,340) |
| Bullish; 3-4 | 47.5% (8,173/17,205) | 48.1% (8,241/17,131) | 48.1% (6,004/12,490) | 47.7% (3,933/8,238) | 47.4% (389/821) |
| Bullish; 5-7 | 47.7% (4,453/9,328) | 48.8% (4,392/8,998) | 48.9% (3,302/6,755) | 48.1% (2,142/4,455) | 49.4% (215/435) |
| Bullish; 8+ | 48.6% (1,542/3,174) | 48.8% (1,514/3,104) | 48.5% (1,161/2,393) | 46.2% (730/1,579) | 56.1% (88/157) |

### GC 10RXV

| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| Bearish; 1-2 | 48.7% (7,309/15,012) | 48.9% (6,622/13,541) | 49.7% (5,048/10,148) | 48.5% (3,116/6,424) | 49.9% (279/559) |
| Bearish; 3-4 | 49.1% (4,215/8,588) | 47.2% (3,781/8,009) | 48.3% (2,868/5,936) | 48.2% (1,853/3,841) | 51.9% (175/337) |
| Bearish; 5-7 | 46.7% (2,219/4,750) | 47.6% (2,087/4,387) | 48.1% (1,566/3,258) | 51.0% (1,068/2,094) | 57.1% (105/184) |
| Bearish; 8+ | 47.0% (810/1,724) | 48.6% (802/1,650) | 45.1% (575/1,274) | 48.9% (405/829) | 55.6% (45/81) |
| Bullish; 1-2 | 50.4% (7,838/15,550) | 49.4% (6,920/14,015) | 49.8% (5,145/10,332) | 50.6% (3,345/6,610) | 57.1% (322/564) |
| Bullish; 3-4 | 49.0% (4,190/8,558) | 48.5% (3,767/7,768) | 48.1% (2,830/5,888) | 48.8% (1,859/3,808) | 49.1% (172/350) |
| Bullish; 5-7 | 48.6% (2,206/4,535) | 49.2% (2,102/4,276) | 48.7% (1,592/3,272) | 48.1% (992/2,064) | 55.3% (114/206) |
| Bullish; 8+ | 49.7% (785/1,581) | 52.8% (799/1,514) | 51.2% (587/1,146) | 49.7% (385/774) | 58.2% (57/98) |

### NQ 10RXV

| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| Bearish; 1-2 | 48.6% (21,718/44,654) | 49.2% (26,951/54,780) | 47.1% (43,257/91,908) | 48.2% (37,477/77,674) | 48.4% (3,277/6,766) |
| Bearish; 3-4 | 48.0% (12,381/25,788) | 48.3% (15,349/31,801) | 46.3% (24,987/53,944) | 47.7% (21,493/45,066) | 46.2% (1,789/3,876) |
| Bearish; 5-7 | 47.3% (6,662/14,084) | 47.4% (8,199/17,285) | 46.1% (13,498/29,296) | 47.5% (11,897/25,060) | 49.5% (976/1,973) |
| Bearish; 8+ | 47.2% (2,635/5,586) | 47.2% (3,132/6,631) | 45.3% (5,216/11,507) | 46.5% (4,403/9,460) | 50.5% (416/823) |
| Bullish; 1-2 | 49.2% (22,324/45,389) | 49.6% (27,269/54,982) | 47.3% (43,590/92,137) | 48.5% (37,771/77,822) | 48.8% (3,353/6,869) |
| Bullish; 3-4 | 48.3% (12,479/25,843) | 48.2% (15,388/31,894) | 45.7% (24,572/53,808) | 47.1% (21,482/45,617) | 46.8% (1,775/3,793) |
| Bullish; 5-7 | 47.6% (6,642/13,961) | 47.9% (8,310/17,350) | 46.3% (13,541/29,248) | 46.6% (11,523/24,715) | 48.1% (967/2,012) |
| Bullish; 8+ | 48.7% (2,465/5,061) | 47.2% (3,121/6,610) | 46.1% (5,077/11,005) | 47.4% (4,378/9,236) | 47.3% (366/773) |

### NQ 20RXV

| C1 direction; prior bars | Asia | London/pre-NY | NY morning | NY afternoon | Transition |
|---|---:|---:|---:|---:|---:|
| Bearish; 1-2 | 50.1% (7,297/14,557) | 50.8% (8,971/17,671) | 50.5% (16,442/32,547) | 50.6% (12,945/25,600) | 50.9% (1,062/2,085) |
| Bearish; 3-4 | 49.1% (4,080/8,318) | 48.6% (4,949/10,176) | 48.6% (9,138/18,812) | 48.5% (7,129/14,698) | 48.0% (608/1,266) |
| Bearish; 5-7 | 48.4% (2,250/4,645) | 49.2% (2,758/5,609) | 47.6% (4,871/10,242) | 48.7% (3,951/8,112) | 47.7% (325/681) |
| Bearish; 8+ | 48.3% (858/1,775) | 49.0% (1,062/2,167) | 45.7% (1,932/4,231) | 48.0% (1,550/3,232) | 55.1% (158/287) |
| Bullish; 1-2 | 50.9% (7,537/14,806) | 50.7% (8,927/17,623) | 50.0% (16,179/32,381) | 50.6% (12,887/25,482) | 52.7% (1,137/2,159) |
| Bullish; 3-4 | 49.3% (4,157/8,436) | 48.2% (5,000/10,380) | 48.5% (9,121/18,791) | 48.3% (7,207/14,926) | 49.1% (635/1,293) |
| Bullish; 5-7 | 49.1% (2,190/4,460) | 48.3% (2,665/5,518) | 48.1% (5,037/10,473) | 47.6% (3,833/8,053) | 47.8% (319/667) |
| Bullish; 8+ | 48.1% (803/1,671) | 48.4% (1,015/2,099) | 47.2% (1,917/4,065) | 49.6% (1,563/3,151) | 53.0% (159/300) |

## Detailed reads and time stability

The baseline for these rows is **all prior-run lengths on the same chart, C1 direction, and session window**. The 95% difference interval accounts for shared session dates; the familywise interval covers the frozen 210 main comparisons. Three-block differences use 2019–2021, 2022–2023, and 2024–2026, respectively. The recent block was previously inspected in older RXV research and is not pristine out-of-sample evidence.

| Chart; C1; prior bars; window | C2 follows | C2+C3 follows | Dates; events/date | Difference vs baseline | 95% CI for difference | Bonferroni CI | Three-block differences |
|---|---:|---:|---:|---:|---:|---:|---:|
| ES 5; bearish; 5-7; london_pre_ny | 75.0% (2,975/3,968) | 47.6% (1,889/3,968) [46.1%–49.2%] | 1,308; 3.0 | -0.59 pp vs 48.2% (12,674/26,297) | -2.03 to +0.85 pp | -3.28 to +2.10 pp | -2.07, +0.52, -0.53 pp |
| GC 10; bullish; 8+; london_pre_ny | 79.2% (1,199/1,514) | 52.8% (799/1,514) [50.3%–55.3%] | 698; 2.2 | +3.49 pp vs 49.3% (13,588/27,573) | +1.10 to +5.89 pp | -1.00 to +7.99 pp | +6.43, +4.20, +2.81 pp |
| ES 6; bearish; 5-7; ny_morning | 71.9% (3,097/4,310) | 45.2% (1,946/4,310) [43.6%–46.7%] | 1,329; 3.2 | -3.28 pp vs 48.4% (13,734/28,360) | -4.64 to -1.91 pp | -5.84 to -0.71 pp | -3.59, -2.48, -3.59 pp |
| NQ 20; bearish; 8+; ny_morning | 72.9% (3,086/4,231) | 45.7% (1,932/4,231) [44.2%–47.2%] | 1,372; 3.1 | -3.53 pp vs 49.2% (32,383/65,832) | -4.98 to -2.07 pp | -6.25 to -0.80 pp | -7.58, -0.34, -3.69 pp |

For all 210 cells, [headline screen](tables/headline_screen.csv) records support and the prespecified positive decision. [Period estimates](tables/period.csv) contain numerator, denominator, session dates, events/date, intervals, and matched block baseline for every cell. 6 downward Bonferroni intervals appear in the full screen; each also has negative differences in all three blocks. They are descriptive checks in overlapping RXV settings.

## Candle and prior-trend structure

The following example fixes ES 5RXV, bearish C1, a 5–7 bar prior bullish run, and London/pre-NY. It compares each prespecified feature within that same run-length group and window. These are separate one-feature splits, not a combined predictive model.

| Feature at C1 close | Value | C2+C3 follows | 95% CI | Session dates; events/date | Difference vs matched group |
|---|---|---:|---:|---:|---:|
| C1 body ≥70% | True | 47.3% (1,416/2,991) | 45.5%–49.2% | 1,158; 2.6 | -0.26 pp |
| C1 body ≥70% | False | 48.4% (473/977) | 45.4%–51.4% | 619; 1.6 | +0.81 pp |
| C1 directional close ≥80% | True | 47.6% (1,888/3,965) | 46.1%–49.2% | 1,308; 3.0 | +0.01 pp |
| C1 directional close ≥80% | False | 33.3% (1/3) | 0.0%–98.7% | 3; 1.0 | -14.27 pp |
| C1 opening-side wick <20% | True | 46.6% (1,120/2,403) | 44.6%–48.6% | 1,046; 2.3 | -1.00 pp |
| C1 opening-side wick <20% | False | 49.1% (769/1,565) | 46.7%–51.5% | 816; 1.9 | +1.53 pp |
| C1 close beyond preceding extreme | True | 47.0% (1,203/2,559) | 45.0%–49.0% | 1,068; 2.4 | -0.60 pp |
| C1 close beyond preceding extreme | False | 48.7% (686/1,409) | 46.1%–51.3% | 814; 1.7 | +1.08 pp |
| Prior mean terminal-side wick <20% | True | 47.6% (1,888/3,966) | 46.1%–49.2% | 1,308; 3.0 | -0.00 pp |
| Prior mean terminal-side wick <20% | False | 50.0% (1/2) | 0.0%–100.0% | 2; 1.0 | +2.39 pp |
| Prior net movement ≥0.75 RXV/bar | True | 47.6% (1,889/3,968) | 46.1%–49.2% | 1,308; 3.0 | +0.00 pp |
| Prior median formation proxy <60 s | True | 47.4% (894/1,886) | 45.1%–49.7% | 576; 3.3 | -0.20 pp |
| Prior median formation proxy <60 s | False | 47.8% (995/2,082) | 45.7%–49.9% | 1,175; 1.8 | +0.18 pp |

A low-contrast feature is not a useful discriminator here: favorable close location and prior net-movement threshold have almost no false cases in this example. The apparent entire-run-break effect from earlier work was largely a one-bar pullback identity, so this study tests only the immediately preceding bar's extreme. All [structure cells](tables/structure.csv), including negative and inconclusive ones, remain available.

## Strictly prior larger-chart context

Pairs are ES 4→5, ES 5→6, GC 6→10, and NQ 10→20. The larger bar must have a strict completion proxy **before** C1's proxy in the same inferred session. Equal-second larger completions are excluded from this primary paired table. Against means C1 opposes the latest completed larger bar; aligned means a snapback into its direction. No later larger-chart bar is attached. The table holds prior run length at 5–7 bars and shows both directions separately.

| Pair; C1 | Context | C2+C3 follows | 95% CI | Dates; events/date | Difference vs pair/bin baseline |
|---|---|---:|---:|---:|---:|
| ES 4→5; bearish | against | 46.5% (9,436/20,301) | 45.8%–47.2% | 1,730; 11.7 | +0.02 pp |
| ES 4→5; bearish | aligned | 46.2% (700/1,514) | 43.7%–48.8% | 879; 1.7 | -0.23 pp |
| ES 4→5; bullish | against | 46.5% (9,334/20,052) | 45.9%–47.2% | 1,712; 11.7 | +0.18 pp |
| ES 4→5; bullish | aligned | 43.9% (626/1,426) | 41.2%–46.6% | 813; 1.8 | -2.47 pp |
| ES 5→6; bearish | against | 46.7% (6,422/13,755) | 45.9%–47.5% | 1,683; 8.2 | -0.04 pp |
| ES 5→6; bearish | aligned | 47.1% (724/1,536) | 44.7%–49.6% | 864; 1.8 | +0.40 pp |
| ES 5→6; bullish | against | 46.8% (6,400/13,673) | 46.0%–47.6% | 1,633; 8.4 | -0.18 pp |
| ES 5→6; bullish | aligned | 48.6% (743/1,528) | 46.2%–51.1% | 870; 1.8 | +1.64 pp |
| GC 6→10; bearish | against | 47.2% (13,619/28,844) | 46.6%–47.9% | 1,741; 16.6 | -0.05 pp |
| GC 6→10; bearish | aligned | 49.6% (280/564) | 45.6%–53.7% | 376; 1.5 | +2.38 pp |
| GC 6→10; bullish | against | 48.5% (13,684/28,187) | 47.9%–49.2% | 1,745; 16.2 | +0.07 pp |
| GC 6→10; bullish | aligned | 45.2% (255/564) | 40.9%–49.5% | 389; 1.4 | -3.27 pp |
| NQ 10→20; bearish | against | 47.0% (38,749/82,419) | 46.7%–47.4% | 1,779; 46.3 | -0.02 pp |
| NQ 10→20; bearish | aligned | 47.3% (2,392/5,059) | 45.8%–48.7% | 1,460; 3.5 | +0.25 pp |
| NQ 10→20; bullish | against | 46.9% (38,530/82,067) | 46.6%–47.3% | 1,769; 46.4 | -0.03 pp |
| NQ 10→20; bullish | aligned | 47.4% (2,372/5,001) | 46.0%–48.9% | 1,446; 3.5 | +0.45 pp |

The [session-resolved larger table](tables/larger.csv) and [all-bin larger table](tables/larger_aggregate.csv) provide their exact matched baselines and intervals. Thin aligned extended-run cells, especially GC 6 after 8+ bars, should not be generalized.

A one-bar opposing pullback that then aligns with the larger chart is a distinct setup. The next-bar rate in this long-history, strictly timed sample is 77.2%–79.5%; the **two-more** rate is 48.5%–50.6%. Its baseline is all one-bar paired signals on the same chart and direction. This must not be substituted for a first reversal after an extended trend. [The full one-bar table](tables/onebar_larger.csv) records both contexts, directions, intervals, and differences.

## Subsequent run lengths and immediate resumption

[The exact run-length distribution](tables/run_lengths.csv) contains every observed number of subsequent C1-direction bars, including zero, with a separate right-censor flag. Its rows provide counts, denominator, session dates, events/date, share, and 95% session-cluster intervals. For a compact example, these are ES 5RXV completed runs of exactly 0–5 more bars; longer lengths and censored rows remain in the full table.

| C1 direction | Exact subsequent bars | Count / eligible | Share [95% CI] | Dates; events/date |
|---|---:|---:|---:|---:|
| bearish | 0 | 31,184/126,449 | 24.7% [24.4%–24.9%] | 1,783; 70.9 |
| bearish | 1 | 34,185/126,449 | 27.0% [26.8%–27.3%] | 1,783; 70.9 |
| bearish | 2 | 21,466/126,449 | 17.0% [16.8%–17.2%] | 1,783; 70.9 |
| bearish | 3 | 13,878/126,449 | 11.0% [10.8%–11.1%] | 1,783; 70.9 |
| bearish | 4 | 9,039/126,449 | 7.1% [7.0%–7.3%] | 1,783; 70.9 |
| bearish | 5 | 5,928/126,449 | 4.7% [4.6%–4.8%] | 1,783; 70.9 |
| bullish | 0 | 31,237/126,311 | 24.7% [24.5%–25.0%] | 1,783; 70.8 |
| bullish | 1 | 34,007/126,311 | 26.9% [26.7%–27.2%] | 1,783; 70.8 |
| bullish | 2 | 21,175/126,311 | 16.8% [16.6%–17.0%] | 1,783; 70.8 |
| bullish | 3 | 13,916/126,311 | 11.0% [10.8%–11.2%] | 1,783; 70.8 |
| bullish | 4 | 9,127/126,311 | 7.2% [7.1%–7.4%] | 1,783; 70.8 |
| bullish | 5 | 5,952/126,311 | 4.7% [4.6%–4.8%] | 1,783; 70.8 |

A doji ends the run and is tabulated separately in the [overall outcome table](tables/overall.csv). Immediate original-trend resumption means C2 closes in the old trend's direction; a C2 doji is neither resumption nor continuation. The three-more outcome requires C2, C3, and C4, and has its own eligible denominator.

## Same-second and GC sensitivities

The [sensitivity table](tables/sensitivity.csv) reintroduces equal-second larger completions using the last strictly earlier state, C1 same-second completions with strict C2/C3 horizons, then both ambiguities. These are uncertainty checks, not primary estimates. Across the four pairs, the absolute two-more rates move modestly under these choices. GC 6 and 10 also include the five excluded 2026 sessions in a separate comparison; the overall rates change: GC 6 from 48.15% to 48.06%, and GC 10 from 49.02% to 48.99%. Those small aggregate changes do not make the missing bars safe for a session-specific claim.

## Input audit, exclusions, and source traces

The pinned long-history manifest and all 14 source/enhanced file hashes were checked before extraction. Enhanced timestamps were not converted again. Bar order, source-row continuity, nondecreasing starts, valid OHLC, manifest row counts, completion-status counts, and session counts were checked. The original source files were used for provenance and 3 manual row traces, never mixed into the event population.

| Chart | Enhanced bars | Observed sessions | C1 signals | Primary eligible after GC exclusion | Excluded C1 completion | Excluded horizon/completion | Same-second C1 | Larger equal-second ties |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ES 4 | 1,281,962 | 1,783 | 408,694 | 358,629 | 15,437 | 34,628 | 14,122 | 106,941 |
| ES 5 | 885,222 | 1,783 | 281,003 | 252,760 | 8,673 | 19,570 | 7,359 | 71,174 |
| ES 6 | 647,911 | 1,783 | 205,195 | 187,508 | 5,511 | 12,176 | 4,195 | 0 |
| GC 6 | 1,661,279 | 1,780 | 516,993 | 389,726 | 38,434 | 80,312 | 37,109 | 104,543 |
| GC 10 | 737,194 | 1,780 | 229,181 | 185,535 | 12,273 | 26,492 | 10,964 | 0 |
| NQ 10 | 4,646,126 | 1,783 | 1,436,045 | 1,116,087 | 79,640 | 240,318 | 78,368 | 181,985 |
| NQ 20 | 1,343,643 | 1,783 | 415,188 | 373,445 | 10,247 | 31,496 | 8,914 | 0 |

The two GC charts each lack 2021-04-02, 2023-04-07, and 2026-04-03 relative to ES/NQ. These may reflect closures or export omission; bars were not invented. The primary GC sample excludes 2026-01-28, 02-04, 02-20, 03-19, and 04-02 because the newer exports differ materially from the older overlaps, including a documented gap on March 19. The [import/overlap audit](../../../docs/range-xv-long-history-20260924.md) found differences on 166 of 534 shared GC 6 sessions and 119 of 534 GC 10 sessions; the remaining differing dates have not been repaired or filled. Treat GC estimates as conditional on this export. The other charts are analyzed only from the long-history snapshot. See [checks](checks.json), [extraction audit](audit.json), and [input lock](inputs.lock.json).

Three ES 5RXV signals were reconciled against literal source CSV rows and the corresponding enhanced rows:

| Session date | C1 source row | Prior rows | C2/C3 rows | Directions (prior,C1,C2,C3) | Two-more outcome | C1 completion NY wall time | Larger equal-second tie |
|---|---:|---:|---:|---|---|---|---|
| 2019-11-04 | 55 | 48-54 | 56/57 | 1x7,-1,1,1 | False | 2019-11-04 03:14:05 | False |
| 2019-12-05 | 1,250 | 1244-1249 | 1251/1252 | 1x6,-1,-1,-1 | True | 2019-12-05 07:18:15 | False |
| 2019-12-13 | 1,654 | 1649-1653 | 1655/1656 | 1x5,-1,-1,-1 | True | 2019-12-13 08:41:21 | True |

For example, ES 5RXV source rows 1244–1249 are six bullish bars; row 1250 is bearish, and rows 1251–1252 are bearish. All three have strictly later within-session completion proxies, so row 1250 counts as a two-more success. Row 55 on 2019-11-04 follows seven bullish bars, but rows 56–57 turn bullish and fail. Row 1654 illustrates an equal-second larger-chart tie; its single-chart outcome remains eligible while the primary paired analysis excludes the tie. The [trace table](tables/real_event_traces.csv) pins these identities.

## Uncertainty, multiplicity, and limits

For each reported rate, the saved tables provide numerator, eligible denominator, distinct session dates, events/date, and a 95% interval based on session-cluster sandwich variance. Matched differences use a joint session-cluster variance. Main positive contrasts use a two-sided Bonferroni interval over 210 prespecified cells, support of at least 300 events, 100 dates, and 2 events/date, plus positive differences in all three periods with at least 30 dates each. Structure and larger-context splits are descriptive. Overlapping signals within a session and transformations of shared trades remain dependent; the cluster interval handles within-session dependence, not dependence across chart settings.

The next-bar-start timestamp is a completion proxy, not the final trade time. Same-second order and exact intrabar sequence are unknown. Range XV construction, contracts/rolls, data-feed provenance, and ATAS timezone settings remain unverified. Year/period differences are retrospective; 2024–2026 was already studied. No probability here establishes a profitable trade. Earlier payoff work found that large failures can outweigh frequent small continuations; stops, fills, and costs are not measured here.

## Reproduction and evidence

The [run manifest](manifest.json) records the frozen plan/settings, input hashes, Git revision and dirty source snapshot, environment lock, exact commands, checks, and artifact hashes. The seven [Parquet event ledgers](events.manifest.json) retain event-level rows. The numeric tables are the authority for every displayed rate; this renderer only selects and formats saved rows. The study README gives the repeatable command sequence. This is a local evidence bundle and has no web publication source.
