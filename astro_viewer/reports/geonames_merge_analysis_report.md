# GeoNames Merge Analysis Report

Source: `C:/Users/beast/PycharmProjects/NightScope/astro_viewer/data/cities15000.txt`
Deduplication radius: 5.0 km

This report reconstructs the historical 5,857 merge run using the legacy importer behavior that treated country, country code, and admin region as city aliases. It also computes the merge count with the corrected importer behavior for comparison.

## Summary

| Metric | Legacy run | Corrected importer replay |
| --- | --- | --- |
| Merged records | 5857 | 228 |
| Average distance | 3.069 km | 1.587 km |
| Max distance | 4.997 km | 4.948 km |
| Suspicious > 1 km | 5511 | 127 |
| Suspicious > 5 km | 0 | 0 |
| Suspicious > 10 km | 0 | 0 |

## Count By Merge Reason

| Reason | Legacy count | Corrected importer count |
| --- | --- | --- |
| alias merge | 98 | 110 |
| same coordinates | 5 | 0 |
| near coordinates | 5638 | 1 |
| normalized name match | 116 | 117 |
| other | 0 | 0 |

Reason definitions:

- `normalized name match`: canonical or ASCII city names match after normalization.
- `alias merge`: source and target share a non-context alternate city name.
- `same coordinates`: merge was effectively driven only by context aliases, but coordinates are within 50 m.
- `near coordinates`: merge was effectively driven only by context aliases, and coordinates are within the dedupe radius but farther than 50 m.
- `other`: merge did not fit the categories above.

## Top 100 Merge Examples By Distance

| # | Reason | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | near coordinates | 4.997 km | LT | Europe/Vilnius | 8714608: Karoliniškės / Karoliniskes pop=31200 @ 54.69034,25.21903 | 17458: Fabijoniškės / Fabijoniskes pop=37000 @ 54.73333,25.24167 | alias intersection: 65, lt |
| 2 | near coordinates | 4.996 km | IN | Asia/Kolkata | 13353494: Panangad / Panangad pop=15630 @ 10.27284,76.17475 | 13134: Kodungallūr / Kodungallur pop=60190 @ 10.23263,76.19513 | alias intersection: 13, in |
| 3 | near coordinates | 4.994 km | IN | Asia/Kolkata | 13353560: Vilappil / Vilappil pop=36212 @ 8.52218,77.04001 | 14820: Vilavoorkkal / Vilavoorkkal pop=31761 @ 8.48093,77.02204 | alias intersection: 13, in |
| 4 | near coordinates | 4.993 km | BR | America/Sao_Paulo | 11962394: Belem / Belem pop=55785 @ -23.53760,-46.59482 | 97: Sao Paulo / Sao Paulo pop=12400232 @ -23.55580,-46.63960 | alias intersection: 27, br |
| 5 | near coordinates | 4.992 km | FR | Europe/Paris | 3023924: Conflans-Sainte-Honorine / Conflans-Sainte-Honorine pop=36358 @ 49.00158,2.09694 | 9693: Saint-Ouen-l'Aumône / Saint-Ouen-l'Aumone pop=30290 @ 49.04353,2.12134 | alias intersection: 11, fr |
| 6 | near coordinates | 4.992 km | ES | Europe/Madrid | 3126890: Cambre / Cambre pop=23231 @ 43.29438,-8.34736 | 9176: Oleiros / Oleiros pop=35559 @ 43.33333,-8.31667 | alias intersection: 58, es |
| 7 | near coordinates | 4.992 km | NL | Europe/Amsterdam | 2758598: Borne / Borne pop=23877 @ 52.30136,6.74820 | 19523: Hengelo / Hengelo pop=82311 @ 52.26583,6.79306 | alias intersection: 15, nl |
| 8 | near coordinates | 4.992 km | CL | America/Santiago | 3888214: Hacienda La Calera / Hacienda La Calera pop=49106 @ -32.78333,-71.21667 | 4559: La Cruz / La Cruz pop=17310 @ -32.82748,-71.22634 | alias intersection: 01, cl |
| 9 | near coordinates | 4.989 km | KR | Asia/Seoul | 1882056: Sinhyeon / Sinhyeon pop=82560 @ 34.88250,128.62667 | 17172: Kyosai / Kyosai pop=72124 @ 34.85028,128.58861 | alias intersection: 20, kr |
| 10 | near coordinates | 4.988 km | IN | Asia/Kolkata | 13353536: Talikkulam / Talikkulam pop=25507 @ 10.44036,76.09483 | 14803: Karamuck / Karamuck pop=17757 @ 10.48421,76.10445 | alias intersection: 13, in |
| 11 | near coordinates | 4.988 km | UZ | Asia/Tashkent | 1514258: Chortoq / Chortoq pop=53400 @ 41.06924,71.82372 | 27191: Uychi / Uychi pop=29683 @ 41.02900,71.85000 | alias intersection: 06, uz |
| 12 | near coordinates | 4.988 km | US | America/Los_Angeles | 5378771: Oceanside / Oceanside pop=175691 @ 33.19587,-117.37948 | 26513: Carlsbad / Carlsbad pop=114746 @ 33.15809,-117.35059 | alias intersection: ca, us |
| 13 | near coordinates | 4.988 km | HK | Asia/Hong_Kong | 12719443: Wu Kai Sha / Wu Kai Sha pop=23511 @ 22.43016,114.24212 | 11005: Tai Mei Tuk / Tai Mei Tuk pop=17544 @ 22.47447,114.23458 | alias intersection: hk |
| 14 | near coordinates | 4.983 km | ES | Europe/Madrid | 6544103: Horta-Guinardó / Horta-Guinardo pop=168092 @ 41.41849,2.16770 | 9131: Santa Coloma de Gramenet / Santa Coloma de Gramenet pop=217741 @ 41.45152,2.20810 | alias intersection: 56, es |
| 15 | near coordinates | 4.983 km | PS | Asia/Gaza | 6967865: Al Qarārah / Al Qararah pop=19500 @ 31.37389,34.34085 | 20995: Khān Yūnis / Khan Yunis pop=173183 @ 31.34018,34.30627 | alias intersection: gz, ps |
| 16 | near coordinates | 4.981 km | PT | Europe/Lisbon | 2272005: Alfornelos / Alfornelos pop=27093 @ 38.76098,-9.20508 | 21036: Ramada / Ramada pop=66231 @ 38.80368,-9.18770 | alias intersection: 14, pt |
| 17 | near coordinates | 4.981 km | US | America/New_York | 5204783: Oxford Circle / Oxford Circle pop=48856 @ 40.05011,-75.07184 | 26299: Bustleton / Bustleton pop=32655 @ 40.08261,-75.03156 | alias intersection: pa, us |
| 18 | near coordinates | 4.981 km | CN | Asia/Shanghai | 1908004: Wenquan / Wenquan pop=18314 @ 34.65193,105.05352 | 5198: Simen / Simen pop=27168 @ 34.62222,105.01278 | alias intersection: 15, cn |
| 19 | near coordinates | 4.980 km | JP | Asia/Tokyo | 10963038: Ōjima / Ojima pop=63254 @ 35.68917,139.83282 | 16001: Sumida / Sumida pop=453093 @ 35.73289,139.82085 | alias intersection: 40, jp |
| 20 | near coordinates | 4.980 km | IN | Asia/Kolkata | 10925345: Chēmanchēri / Chemancheri pop=34819 @ 11.40482,75.72363 | 12422: Koyilandy / Koyilandy pop=71873 @ 11.43810,75.69306 | alias intersection: 13, in |
| 21 | near coordinates | 4.979 km | CN | Asia/Urumqi | 12450868: Tuohula / Tuohula pop=18800 @ 37.24227,79.69283 | 4724: Qaraqash / Qaraqash pop=66541 @ 37.27246,79.73438 | alias intersection: 13, cn |
| 22 | near coordinates | 4.979 km | FI | Europe/Helsinki | 847422: Myyrmäki / Myyrmaeki pop=18393 @ 60.26711,24.84713 | 9532: Pitäjänmäki / Pitaejaenmaeki pop=27761 @ 60.22287,24.86103 | alias intersection: 01, fi |
| 23 | near coordinates | 4.976 km | FR | Europe/Paris | 2992404: Montigny-lès-Cormeilles / Montigny-les-Cormeilles pop=17910 @ 48.98201,2.20035 | 9661: Taverny / Taverny pop=27271 @ 49.02542,2.21691 | alias intersection: 11, fr |
| 24 | near coordinates | 4.976 km | SE | Europe/Stockholm | 2707462: Hässelby Villastad / Haesselby Villastad pop=19000 @ 59.38000,17.80867 | 22617: Jakobsberg / Jakobsberg pop=24046 @ 59.42268,17.83508 | alias intersection: 26, se |
| 25 | near coordinates | 4.975 km | DE | Europe/Berlin | 2874455: Mahlsdorf / Mahlsdorf pop=29757 @ 52.50935,13.61373 | 7639: Marzahn / Marzahn pop=111508 @ 52.54525,13.56983 | alias intersection: 16, de |
| 26 | near coordinates | 4.975 km | GB | Europe/London | 2652249: Coulsdon / Coulsdon pop=25530 @ 51.32002,-0.14088 | 10073: Wallington / Wallington pop=72000 @ 51.36404,-0.15368 | alias intersection: eng, gb |
| 27 | near coordinates | 4.974 km | IN | Asia/Kolkata | 13494717: Puzhal / Puzhal pop=31665 @ 13.16475,80.20385 | 12616: Pādiyanallūr / Padiyanallur pop=23819 @ 13.20037,80.17606 | alias intersection: 25, in |
| 28 | near coordinates | 4.973 km | SG | Asia/Singapore | 1882101: Serangoon New Town / Serangoon New Town pop=116900 @ 1.35083,103.87083 | 22645: Yio Chu Kang / Yio Chu Kang pop=28350 @ 1.39111,103.85139 | alias intersection: 00, sg |
| 29 | near coordinates | 4.973 km | SG | Asia/Singapore | 1880469: Marsiling / Marsiling pop=22000 @ 1.43254,103.77407 | 22646: Yew Tee / Yew Tee pop=39100 @ 1.39665,103.74738 | alias intersection: 03, sg |
| 30 | near coordinates | 4.973 km | IT | Europe/Rome | 13607968: Circoiscrizione IV / Circoiscrizione IV pop=98787 @ 45.08125,7.63188 | 15437: Venaria Reale / Venaria Reale pop=50000 @ 45.12597,7.63136 | alias intersection: 12, it |
| 31 | near coordinates | 4.973 km | TW | Asia/Taipei | 1665443: Yuanlin / Yuanlin pop=124725 @ 23.95671,120.57608 | 23862: Yongjing / Yongjing pop=35365 @ 23.92148,120.54594 | alias intersection: 04, tw |
| 32 | near coordinates | 4.972 km | US | Pacific/Honolulu | 13645944: Schofield-Wheeler / Schofield-Wheeler pop=20452 @ 21.48394,-158.04681 | 27059: Mililani Town / Mililani Town pop=27629 @ 21.45040,-158.01503 | alias intersection: hi, us |
| 33 | near coordinates | 4.972 km | RU | Europe/Moscow | 517161: Novyye Cherëmushki / Novyye Cheremushki pop=101000 @ 55.70000,37.58333 | 21345: Zyuzino / Zyuzino pop=121000 @ 55.65608,37.56846 | alias intersection: 48, ru |
| 34 | near coordinates | 4.972 km | BE | Europe/Brussels | 2796542: Harelbeke / Harelbeke pop=25978 @ 50.85343,3.30935 | 1055: Zwevegem / Zwevegem pop=23358 @ 50.81268,3.33848 | alias intersection: be, vlg |
| 35 | near coordinates | 4.971 km | CA | America/Toronto | 6183590: Woburn / Woburn pop=53485 @ 43.76657,-79.22773 | 3811: Cliffcrest / Cliffcrest pop=17123 @ 43.72192,-79.23091 | alias intersection: 08, ca |
| 36 | near coordinates | 4.971 km | SR | America/Paramaribo | 8220838: Munder Buiten / Munder Buiten pop=17234 @ 5.84116,-55.18247 | 22835: Flora / Flora pop=19538 @ 5.80000,-55.20000 | alias intersection: 16, sr |
| 37 | near coordinates | 4.969 km | US | America/New_York | 4955840: Wilmington / Wilmington pop=22325 @ 42.54648,-71.17367 | 25819: Burlington / Burlington pop=24498 @ 42.50482,-71.19561 | alias intersection: ma, us |
| 38 | near coordinates | 4.968 km | VE | America/Caracas | 3647549: Cagua / Cagua pop=119033 @ 10.18634,-67.45935 | 27279: Turmero / Turmero pop=344700 @ 10.22856,-67.47421 | alias intersection: 04, ve |
| 39 | near coordinates | 4.968 km | IT | Europe/Rome | 3174679: Lissone / Lissone pop=37353 @ 45.61236,9.23985 | 15482: Seregno / Seregno pop=42760 @ 45.65002,9.20548 | alias intersection: 09, it |
| 40 | near coordinates | 4.967 km | DE | Europe/Berlin | 2936977: Dillingen / Dillingen pop=21526 @ 49.35557,6.72781 | 7450: Saarlouis / Saarlouis pop=38333 @ 49.31366,6.75154 | alias intersection: 09, de |
| 41 | near coordinates | 4.967 km | DE | Europe/Berlin | 2943573: Bruchköbel / Bruchkoebel pop=20509 @ 50.17853,8.92315 | 7829: Hanau am Main / Hanau am Main pop=88648 @ 50.13423,8.91418 | alias intersection: 05, de |
| 42 | near coordinates | 4.967 km | TN | Africa/Tunis | 2473420: Ouardenine / Ouardenine pop=18287 @ 35.70915,10.67397 | 23398: Maatmeur / Maatmeur pop=18996 @ 35.75167,10.69083 | alias intersection: 16, tn |
| 43 | near coordinates | 4.967 km | ZA | Africa/Johannesburg | 12718834: Thubelihle / Thubelihle pop=15876 @ -26.21551,29.29164 | 27891: Kriel / Kriel pop=18255 @ -26.25000,29.26000 | alias intersection: 07, za |
| 44 | near coordinates | 4.966 km | PT | Europe/Lisbon | 2265726: Moscavide e Portela / Moscavide e Portela pop=22488 @ 38.77929,-9.10222 | 21032: São João da Talha / Sao Joao da Talha pop=18925 @ 38.82378,-9.09719 | alias intersection: 14, pt |
| 45 | near coordinates | 4.966 km | CA | America/Toronto | 6137579: Saint-Charles-Borromée / Saint-Charles-Borromee pop=15285 @ 46.05007,-73.46586 | 3865: Joliette / Joliette pop=34772 @ 46.01640,-73.42360 | alias intersection: 10, ca |
| 46 | near coordinates | 4.966 km | DZ | Africa/Algiers | 2491911: Khemis Miliana / Khemis Miliana pop=80512 @ 36.26104,2.22015 | 8349: Miliana / Miliana pop=43366 @ 36.30554,2.22480 | alias intersection: 35, dz |
| 47 | near coordinates | 4.965 km | IN | Asia/Kolkata | 10337414: Singānuram / Singanuram pop=20061 @ 18.82218,79.50171 | 12696: Nāspur / Naspur pop=89935 @ 18.84577,79.46165 | alias intersection: 40, in |
| 48 | near coordinates | 4.965 km | IN | Asia/Kolkata | 11655503: Triparappu / Triparappu pop=22401 @ 8.39479,77.26588 | 13071: Kulasegaram / Kulasegaram pop=17267 @ 8.36319,77.29777 | alias intersection: 25, in |
| 49 | near coordinates | 4.965 km | IN | Asia/Kolkata | 1273618: Daman / Daman pop=44282 @ 20.41431,72.83236 | 13198: Khali Kachigam / Khali Kachigam pop=18434 @ 20.38333,72.86667 | alias intersection: 52, in |
| 50 | near coordinates | 4.964 km | VN | Asia/Ho_Chi_Minh | 8657105: Hòa Cường / Hoa Cuong pop=119363 @ 16.04314,108.18209 | 27609: Da Nang / Da Nang pop=1276000 @ 16.06778,108.22083 | alias intersection: 48, vn |
| 51 | near coordinates | 4.964 km | US | America/New_York | 4504225: South Vineland / South Vineland pop=58122 @ 39.44595,-75.02879 | 25186: Millville / Millville pop=28230 @ 39.40206,-75.03934 | alias intersection: nj, us |
| 52 | near coordinates | 4.963 km | IN | Asia/Kolkata | 11556989: Ālampālaiyam / Alampalaiyam pop=20286 @ 11.36353,77.76773 | 13685: Erode / Erode pop=521891 @ 11.34280,77.72741 | alias intersection: 25, in |
| 53 | near coordinates | 4.962 km | RO | Europe/Bucharest | 11048322: Sector 5 / Sector 5 pop=271575 @ 44.38808,26.07144 | 67: Bucharest / Bucharest pop=1877155 @ 44.42680,26.10250 | alias intersection: 10, ro |
| 54 | near coordinates | 4.962 km | AE | Asia/Dubai | 6691091: Al Karama / Al Karama pop=75560 @ 25.24004,55.30106 | 122: Dubai / Dubai pop=40997 @ 25.20480,55.27080 | alias intersection: 03, ae |
| 55 | near coordinates | 4.961 km | BR | America/Sao_Paulo | 11962427: Jardim Sao Luis / Jardim Sao Luis pop=259377 @ -23.68073,-46.73940 | 3647: Jardim Angela / Jardim Angela pop=311432 @ -23.71636,-46.76872 | alias intersection: 27, br |
| 56 | near coordinates | 4.960 km | DE | Europe/Berlin | 2913195: Haan / Haan pop=29431 @ 51.19382,7.01330 | 7540: Ohligs / Ohligs pop=43063 @ 51.15000,7.00000 | alias intersection: 07, de |
| 57 | near coordinates | 4.960 km | SG | Asia/Singapore | 1880650: Hong Kah / Hong Kah pop=26150 @ 1.35944,103.72278 | 22646: Yew Tee / Yew Tee pop=39370 @ 1.39665,103.74738 | alias intersection: 00, sg |
| 58 | near coordinates | 4.959 km | DE | Europe/Berlin | 2949235: Biebrich / Biebrich pop=38758 @ 50.04150,8.24878 | 7251: Wiesbaden / Wiesbaden pop=288850 @ 50.08601,8.24435 | alias intersection: 05, de |
| 59 | near coordinates | 4.959 km | NZ | Pacific/Auckland | 6232009: Otahuhu / Otahuhu pop=17780 @ -36.93820,174.84019 | 19693: Mangere / Mangere pop=28540 @ -36.96807,174.79875 | alias intersection: e7, nz |
| 60 | near coordinates | 4.958 km | ES | Europe/Madrid | 3123115: Entrevías / Entrevias pop=35399 @ 40.37846,-3.67390 | 51: Madrid / Madrid pop=3255944 @ 40.41680,-3.70380 | alias intersection: 29, es |
| 61 | near coordinates | 4.958 km | CA | America/Toronto | 5884238: Alta Vista / Alta Vista pop=24726 @ 45.38639,-75.65806 | 81: Ottawa / Ottawa pop=0 @ 45.42150,-75.69720 | alias intersection: ca |
| 62 | near coordinates | 4.957 km | CA | America/Toronto | 12156824: Banbury-Don Mills / Banbury-Don Mills pop=27695 @ 43.73766,-79.34972 | 3771: Bayview Village / Bayview Village pop=79440 @ 43.77639,-79.38028 | alias intersection: 08, ca |
| 63 | near coordinates | 4.956 km | JP | Asia/Tokyo | 1861212: Iwakuni / Iwakuni pop=129125 @ 34.16297,132.22000 | 16075: Ōtake / Otake pop=30151 @ 34.20754,132.22063 | alias intersection: jp |
| 64 | alias merge | 4.956 km | JP | Asia/Tokyo | 7279570: Higashimurayama / Higashimurayama pop=151815 @ 35.75459,139.46852 | 15945: Tokorozawa / Tokorozawa pop=344194 @ 35.79916,139.46903 | alias intersection: 40, dong cun shan, jp, 東村山 |
| 65 | near coordinates | 4.956 km | US | America/New_York | 5104404: Sayreville / Sayreville pop=44920 @ 40.45927,-74.36098 | 26082: Old Bridge / Old Bridge pop=23753 @ 40.41483,-74.36543 | alias intersection: nj, us |
| 66 | near coordinates | 4.955 km | PT | Europe/Lisbon | 2740637: Coimbra / Coimbra pop=140796 @ 40.20686,-8.41996 | 21084: São Paulo de Frades / Sao Paulo de Frades pop=41150 @ 40.24678,-8.39402 | alias intersection: 07, pt |
| 67 | near coordinates | 4.955 km | US | America/Chicago | 4885156: Bloomingdale / Bloomingdale pop=22254 @ 41.95753,-88.08090 | 25582: Glendale Heights / Glendale Heights pop=34208 @ 41.91460,-88.06486 | alias intersection: il, us |
| 68 | near coordinates | 4.954 km | MX | America/Mexico_City | 3530123: Coyotepec / Coyotepec pop=35677 @ 19.77722,-99.21295 | 18232: Teoloyucan / Teoloyucan pop=51255 @ 19.74423,-99.18113 | alias intersection: 15, mx |
| 69 | near coordinates | 4.954 km | NL | Europe/Amsterdam | 2758927: Bilthoven / Bilthoven pop=23248 @ 52.13000,5.20139 | 19405: Zeist / Zeist pop=60949 @ 52.09000,5.23333 | alias intersection: 09, nl |
| 70 | near coordinates | 4.953 km | US | America/New_York | 4354573: Fairland / Fairland pop=23681 @ 39.07622,-76.95775 | 24994: Cloverly / Cloverly pop=15126 @ 39.10816,-76.99775 | alias intersection: md, us |
| 71 | near coordinates | 4.952 km | MY | Asia/Kuala_Lumpur | 7779082: Sri Petaling / Sri Petaling pop=50000 @ 3.06881,101.68971 | 18911: Seri Kembangan / Seri Kembangan pop=130252 @ 3.03333,101.71667 | alias intersection: my |
| 72 | near coordinates | 4.952 km | GM | Africa/Banjul | 12640501: New Jeshwang / New Jeshwang pop=20878 @ 13.44735,-16.66500 | 10749: Welingara / Welingara pop=340000 @ 13.40361,-16.67361 | alias intersection: 01, gm |
| 73 | near coordinates | 4.952 km | SG | Asia/Singapore | 1880668: Geylang / Geylang pop=110201 @ 1.31953,103.88689 | 22650: Serangoon / Serangoon pop=144260 @ 1.36278,103.89750 | alias intersection: 00, sg |
| 74 | near coordinates | 4.951 km | RU | Europe/Moscow | 542634: Presnenskiy / Presnenskiy pop=122000 @ 55.75894,37.55816 | 21409: Vorob’yovo / Vorob'yovo pop=130000 @ 55.71667,37.53333 | alias intersection: 48, ru |
| 75 | near coordinates | 4.950 km | MY | Asia/Kuala_Lumpur | 10792382: Putra Heights / Putra Heights pop=60000 @ 2.99361,101.57255 | 18913: Puchong / Puchong pop=375181 @ 3.00000,101.61667 | alias intersection: 12, my |
| 76 | near coordinates | 4.950 km | PE | America/Lima | 3949231: Jacobo Hunter / Jacobo Hunter pop=46092 @ -16.44083,-71.55333 | 19865: Arequipa / Arequipa pop=1008290 @ -16.39899,-71.53747 | alias intersection: 04, pe |
| 77 | near coordinates | 4.947 km | JP | Asia/Tokyo | 1858681: Kōtari / Kotari pop=80608 @ 34.92097,135.70547 | 16154: Mukō / Muko pop=56859 @ 34.96545,135.70415 | alias intersection: 22, jp |
| 78 | near coordinates | 4.947 km | FR | Europe/Paris | 3019897: Ermont / Ermont pop=28117 @ 48.99004,2.25804 | 9661: Taverny / Taverny pop=34284 @ 49.02542,2.21691 | alias intersection: 11, fr |
| 79 | near coordinates | 4.947 km | DZ | Africa/Algiers | 2491913: Khemis el Khechna / Khemis el Khechna pop=46965 @ 36.64997,3.33080 | 8331: Ouled Moussa / Ouled Moussa pop=40692 @ 36.68394,3.36661 | alias intersection: 40, dz |
| 80 | near coordinates | 4.946 km | JP | Asia/Tokyo | 1857046: Minoh / Minoh pop=136868 @ 34.82691,135.47057 | 15932: Toyonaka / Toyonaka pop=401558 @ 34.78244,135.46932 | alias intersection: 32, jp |
| 81 | near coordinates | 4.946 km | CA | America/Toronto | 12626157: Parc-Extension / Parc-Extension pop=33800 @ 45.52951,-73.63176 | 3760: Ahuntsic-Cartierville / Ahuntsic-Cartierville pop=438366 @ 45.56667,-73.66667 | alias intersection: 10, ca |
| 82 | near coordinates | 4.946 km | VN | Asia/Bangkok | 1591493: Bạch Mai / Bach Mai pop=91308 @ 20.98333,105.83333 | 105: Hanoi / Hanoi pop=8053663 @ 21.02780,105.83420 | alias intersection: 01, vn |
| 83 | near coordinates | 4.946 km | NG | Africa/Lagos | 2328811: Nkpor / Nkpor pop=103733 @ 6.15038,6.83042 | 19152: Onitsha / Onitsha pop=1553000 @ 6.14978,6.78569 | alias intersection: 25, ng |
| 84 | near coordinates | 4.945 km | PH | Asia/Manila | 1725919: Bay / Bay pop=33547 @ 14.18368,121.28554 | 20115: Los Baños / Los Banos pop=117030 @ 14.17025,121.24181 | alias intersection: 40, ph |
| 85 | near coordinates | 4.945 km | MY | Asia/Kuala_Lumpur | 1744763: Sentul / Sentul pop=100000 @ 3.18333,101.68333 | 109: Kuala Lumpur / Kuala Lumpur pop=1453975 @ 3.13900,101.68690 | alias intersection: 14, my |
| 86 | near coordinates | 4.944 km | MY | Asia/Kuching | 1733440: Putatan / Putatan pop=78340 @ 5.92580,116.06094 | 18768: Donggongon / Donggongon pop=78086 @ 5.90702,116.10146 | alias intersection: 16, my |
| 87 | near coordinates | 4.944 km | GU | Pacific/Guam | 7268049: Mangilao Village / Mangilao Village pop=15191 @ 13.44761,144.80109 | 10987: Tamuning-Tumon-Harmon Village / Tamuning-Tumon-Harmon Village pop=19685 @ 13.48773,144.78138 | alias intersection: gu |
| 88 | near coordinates | 4.943 km | IL | Asia/Jerusalem | 294577: Karmi’el / Karmi'el pop=46252 @ 32.90951,35.29768 | 11694: Sakhnīn / Sakhnin pop=31702 @ 32.86506,35.29771 | alias intersection: 03, il |
| 89 | near coordinates | 4.941 km | IN | Asia/Kolkata | 11679729: Ariyānkuppam / Ariyankuppam pop=29808 @ 11.89532,79.80709 | 12461: Puducherry / Puducherry pop=657209 @ 11.93381,79.82979 | alias intersection: 22, in |
| 90 | near coordinates | 4.941 km | IN | Asia/Kolkata | 10628607: Aroor / Aroor pop=39214 @ 9.86940,76.30498 | 14281: Arukutti / Arukutti pop=17944 @ 9.86667,76.35000 | alias intersection: 13, in |
| 91 | near coordinates | 4.938 km | US | America/New_York | 4159805: Iona / Iona pop=15369 @ 26.52036,-81.96398 | 24651: Cape Coral / Cape Coral pop=175229 @ 26.56285,-81.94953 | alias intersection: fl, us |
| 92 | near coordinates | 4.938 km | GB | Europe/London | 2639265: Rochford / Rochford pop=16739 @ 51.58198,0.70673 | 10133: Southend-on-Sea / Southend-on-Sea pop=295310 @ 51.53782,0.71433 | alias intersection: eng, gb |
| 93 | near coordinates | 4.938 km | VE | America/Caracas | 3645469: Cocorote / Cocorote pop=52803 @ 10.31954,-68.78298 | 27314: San Felipe / San Felipe pop=206270 @ 10.34010,-68.74297 | alias intersection: 22, ve |
| 94 | near coordinates | 4.936 km | US | America/Chicago | 4904365: Oak Lawn / Oak Lawn pop=56781 @ 41.71087,-87.75811 | 25666: Alsip / Alsip pop=19346 @ 41.66892,-87.73866 | alias intersection: il, us |
| 95 | near coordinates | 4.936 km | US | America/New_York | 4176318: Valrico / Valrico pop=35545 @ 27.93789,-82.23644 | 24641: Bloomingdale / Bloomingdale pop=22711 @ 27.89364,-82.24037 | alias intersection: fl, us |
| 96 | near coordinates | 4.935 km | GH | Africa/Accra | 2298890: Kumasi / Kumasi pop=2544530 @ 6.68848,-1.62443 | 10671: Tafo / Tafo pop=50457 @ 6.73156,-1.61370 | alias intersection: 02, gh |
| 97 | near coordinates | 4.934 km | DE | Europe/Berlin | 2924302: Frohnau / Frohnau pop=16689 @ 52.63336,13.29024 | 7236: Wittenau / Wittenau pop=83972 @ 52.59319,13.32127 | alias intersection: 16, de |
| 98 | near coordinates | 4.933 km | US | America/New_York | 5101717: New Brunswick / New Brunswick pop=57035 @ 40.48622,-74.45182 | 26059: Edison / Edison pop=102548 @ 40.51872,-74.41210 | alias intersection: nj, us |
| 99 | near coordinates | 4.933 km | CA | America/Vancouver | 13495378: Marpole / Marpole pop=27843 @ 49.21359,-123.12979 | 3766: Arbutus Ridge / Arbutus Ridge pop=62030 @ 49.24966,-123.16934 | alias intersection: 02, ca |
| 100 | near coordinates | 4.932 km | IN | Asia/Kolkata | 13157010: Ziauddin Pur / Ziauddin Pur pop=68993 @ 28.70873,77.27654 | 13002: Loni / Loni pop=516082 @ 28.75143,77.29023 | alias intersection: 07, in |

## Top Examples Grouped By Reason

### alias merge

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 4.956 km | JP | Asia/Tokyo | 7279570: Higashimurayama / Higashimurayama pop=151815 @ 35.75459,139.46852 | 15945: Tokorozawa / Tokorozawa pop=344194 @ 35.79916,139.46903 | alias intersection: 40, dong cun shan, jp, 東村山 |
| 2 | 4.882 km | CA | America/Toronto | 5917781: Cartierville / Cartierville pop=34667 @ 45.53118,-73.70358 | 3760: Ahuntsic-Cartierville / Ahuntsic-Cartierville pop=135336 @ 45.56667,-73.66667 | alias intersection: 10, ca, cartierville |
| 3 | 4.766 km | IN | Asia/Kolkata | 1273294: Delhi / Delhi pop=11034555 @ 28.65195,77.23149 | 110: New Delhi / New Delhi pop=505241 @ 28.61390,77.20900 | alias intersection: 07, delhi, dilli, in, na'i dilli, new delhi, नई दिलली |
| 4 | 4.386 km | HK | Asia/Hong_Kong | 1931681: Victoria / Victoria pop=956800 @ 22.28750,114.14417 | 103: Hong Kong / Hong Kong pop=7396076 @ 22.31930,114.16940 | alias intersection: hcw, hk, victoria |
| 5 | 4.340 km | TH | Asia/Bangkok | 7504194: Khwaeng Bang Khae / Khwaeng Bang Khae pop=38915 @ 13.69162,100.40448 | 23164: Phasi Charoen / Phasi Charoen pop=193002 @ 13.71466,100.43691 | alias intersection: 40, khwaeng bang khae, th |
| 6 | 4.327 km | BR | America/Sao_Paulo | 3471039: Balneário Camboriú / Balneario Camboriu pop=139155 @ -26.99056,-48.63472 | 3197: Camboriú / Camboriu pop=85105 @ -27.02528,-48.65444 | alias intersection: 26, br, camboriu |
| 7 | 4.273 km | CN | Asia/Shanghai | 8054802: Xilinhot / Xilinhot pop=349953 @ 43.93889,116.07021 | 6086: Xilin Hot / Xilin Hot pop=120965 @ 43.96667,116.03333 | alias intersection: 20, cn, xi lin hao te, xi lin hao te shi, xilin hot, xilinhaote shi, xilinhot, 锡林浩特 |
| 8 | 4.195 km | US | America/New_York | 4955089: West Springfield / West Springfield pop=27912 @ 42.10704,-72.62037 | 25805: Agawam / Agawam pop=154341 @ 42.06954,-72.61481 | alias intersection: ma, spryngpyld, us, ספרינגפילד |
| 9 | 4.107 km | US | America/New_York | 4951788: Springfield / Springfield pop=154341 @ 42.10148,-72.58981 | 25805: Agawam / Agawam pop=28761 @ 42.06954,-72.61481 | alias intersection: agawam, agawome, ma, us |
| 10 | 3.974 km | ES | Atlantic/Canary | 2515692: La Orotava / La Orotava pop=41833 @ 28.39076,-16.52309 | 8901: Puerto de la Cruz / Puerto de la Cruz pop=32219 @ 28.41686,-16.55085 | alias intersection: 53, es, orotava |

### same coordinates

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.040 km | BR | America/Sao_Paulo | 13512576: Plano Piloto / Plano Piloto pop=198697 @ -15.79411,-47.88250 | 96: Brasilia / Brasilia pop=44354 @ -15.79390,-47.88280 | alias intersection: 07, br |
| 2 | 0.008 km | DE | Europe/Berlin | 6545310: Mitte / Mitte pop=102338 @ 52.52003,13.40489 | 50: Berlin / Berlin pop=3426354 @ 52.52000,13.40500 | alias intersection: 16, de |
| 3 | 0.000 km | JP | Asia/Tokyo | 2112996: Choshi / Choshi pop=58431 @ 35.73333,140.83333 | 16552: Hasaki / Hasaki pop=39209 @ 35.73333,140.83333 | alias intersection: 04, jp |
| 4 | 0.000 km | JP | Asia/Tokyo | 2130306: Furano / Furano pop=21131 @ 43.35000,142.38333 | 16577: Shimo-furano / Shimo-furano pop=25872 @ 43.35000,142.38333 | alias intersection: 12, jp |
| 5 | 0.000 km | RU | Europe/Moscow | 574675: Bol’shaya Setun’ / Bol'shaya Setun' pop=20000 @ 55.71667,37.41667 | 21546: Setun’ / Setun' pop=147497 @ 55.71667,37.41667 | alias intersection: ru |

### near coordinates

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 4.997 km | LT | Europe/Vilnius | 8714608: Karoliniškės / Karoliniskes pop=31200 @ 54.69034,25.21903 | 17458: Fabijoniškės / Fabijoniskes pop=37000 @ 54.73333,25.24167 | alias intersection: 65, lt |
| 2 | 4.996 km | IN | Asia/Kolkata | 13353494: Panangad / Panangad pop=15630 @ 10.27284,76.17475 | 13134: Kodungallūr / Kodungallur pop=60190 @ 10.23263,76.19513 | alias intersection: 13, in |
| 3 | 4.994 km | IN | Asia/Kolkata | 13353560: Vilappil / Vilappil pop=36212 @ 8.52218,77.04001 | 14820: Vilavoorkkal / Vilavoorkkal pop=31761 @ 8.48093,77.02204 | alias intersection: 13, in |
| 4 | 4.993 km | BR | America/Sao_Paulo | 11962394: Belem / Belem pop=55785 @ -23.53760,-46.59482 | 97: Sao Paulo / Sao Paulo pop=12400232 @ -23.55580,-46.63960 | alias intersection: 27, br |
| 5 | 4.992 km | FR | Europe/Paris | 3023924: Conflans-Sainte-Honorine / Conflans-Sainte-Honorine pop=36358 @ 49.00158,2.09694 | 9693: Saint-Ouen-l'Aumône / Saint-Ouen-l'Aumone pop=30290 @ 49.04353,2.12134 | alias intersection: 11, fr |
| 6 | 4.992 km | ES | Europe/Madrid | 3126890: Cambre / Cambre pop=23231 @ 43.29438,-8.34736 | 9176: Oleiros / Oleiros pop=35559 @ 43.33333,-8.31667 | alias intersection: 58, es |
| 7 | 4.992 km | NL | Europe/Amsterdam | 2758598: Borne / Borne pop=23877 @ 52.30136,6.74820 | 19523: Hengelo / Hengelo pop=82311 @ 52.26583,6.79306 | alias intersection: 15, nl |
| 8 | 4.992 km | CL | America/Santiago | 3888214: Hacienda La Calera / Hacienda La Calera pop=49106 @ -32.78333,-71.21667 | 4559: La Cruz / La Cruz pop=17310 @ -32.82748,-71.22634 | alias intersection: 01, cl |
| 9 | 4.989 km | KR | Asia/Seoul | 1882056: Sinhyeon / Sinhyeon pop=82560 @ 34.88250,128.62667 | 17172: Kyosai / Kyosai pop=72124 @ 34.85028,128.58861 | alias intersection: 20, kr |
| 10 | 4.988 km | IN | Asia/Kolkata | 13353536: Talikkulam / Talikkulam pop=25507 @ 10.44036,76.09483 | 14803: Karamuck / Karamuck pop=17757 @ 10.48421,76.10445 | alias intersection: 13, in |

### normalized name match

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 4.589 km | HK | Asia/Hong_Kong | 1819729: Hong Kong / Hong Kong pop=7396076 @ 22.27832,114.17469 | 103: Hong Kong / Hong Kong pop=2232339 @ 22.31930,114.16940 | alias intersection: hk, hong kong |
| 2 | 4.519 km | TW | Asia/Taipei | 1668341: Taipei / Taipei pop=7871900 @ 25.05306,121.52639 | 102: Taipei / Taipei pop=0 @ 25.03300,121.56540 | alias intersection: taipei, tw |
| 3 | 4.290 km | IQ | Asia/Baghdad | 98182: Baghdad / Baghdad pop=7216000 @ 33.34058,44.40088 | 116: Baghdad / Baghdad pop=0 @ 33.31520,44.36610 | alias intersection: baghdad, iq |
| 4 | 4.167 km | ZA | Africa/Johannesburg | 964137: Pretoria / Pretoria pop=2112693 @ -25.74486,28.18783 | 36: Pretoria / Pretoria pop=0 @ -25.74790,28.22930 | alias intersection: pretoria, za |
| 5 | 4.145 km | PK | Asia/Karachi | 1176615: Islamabad / Islamabad pop=601600 @ 33.72148,73.04329 | 114: Islamabad / Islamabad pop=0 @ 33.68440,73.04790 | alias intersection: islamabad, pk |
| 6 | 4.022 km | JP | Asia/Tokyo | 1850147: Tokyo / Tokyo pop=9733276 @ 35.68950,139.69171 | 98: Tokyo / Tokyo pop=0 @ 35.67620,139.65030 | alias intersection: jp, tokyo |
| 7 | 3.606 km | SN | Africa/Dakar | 2253354: Dakar / Dakar pop=2646503 @ 14.69370,-17.44406 | 42: Dakar / Dakar pop=0 @ 14.71670,-17.46770 | alias intersection: dakar, sn |
| 8 | 3.543 km | US | America/Chicago | 4887398: Chicago / Chicago pop=2664452 @ 41.85003,-87.65005 | 80: Chicago / Chicago pop=33878 @ 41.87810,-87.62980 | alias intersection: chicago, il, us |
| 9 | 3.502 km | DZ | Africa/Algiers | 2507480: Algiers / Algiers pop=2364230 @ 36.73225,3.08746 | 39: Algiers / Algiers pop=71722 @ 36.75380,3.05880 | alias intersection: 01, algiers, dz |
| 10 | 3.483 km | UG | Africa/Kampala | 232422: Kampala / Kampala pop=1680600 @ 0.31628,32.58219 | 45: Kampala / Kampala pop=0 @ 0.34760,32.58250 | alias intersection: kampala, ug |

### other

No merge examples for this reason.

## Suspicious Merge Buckets

### Distance > 1 km

| Reason | Count |
| --- | --- |
| alias merge | 74 |
| same coordinates | 0 |
| near coordinates | 5391 |
| normalized name match | 46 |
| other | 0 |

### Distance > 5 km

| Reason | Count |
| --- | --- |
| alias merge | 0 |
| same coordinates | 0 |
| near coordinates | 0 |
| normalized name match | 0 |
| other | 0 |

### Distance > 10 km

| Reason | Count |
| --- | --- |
| alias merge | 0 |
| same coordinates | 0 |
| near coordinates | 0 |
| normalized name match | 0 |
| other | 0 |

## Assessment

- The legacy run produced 5857 merges. Of these, 219 have a strong name/alias or same-coordinate signal, while 5638 are near-coordinate context-only merges.
- Replaying with the corrected importer produces 228 merges, reducing the merge count by 5629.
- A high count of `near coordinates` merges is evidence that the old deduplication was too aggressive because country/admin aliases made unrelated nearby settlements look related.
- Legitimate translated-name merges, including cases like Addis Ababa/Addis Abeba, should remain in the corrected replay because they share real city aliases.
