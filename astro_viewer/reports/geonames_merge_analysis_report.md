# GeoNames Merge Analysis Report

Source: `C:/Users/beast/PycharmProjects/NightScope/astro_viewer/data/cities15000.txt`
Deduplication radius: 5.0 km

This report reconstructs the legacy importer behavior that treated country, country code, and admin region as city aliases. It also computes the merge count with the corrected importer behavior for comparison.

## Summary

| Metric | Legacy run | Corrected importer replay |
| --- | --- | --- |
| Merged records | 5732 | 115 |
| Average distance | 3.127 km | 2.065 km |
| Max distance | 4.998 km | 4.948 km |
| Suspicious > 1 km | 5482 | 85 |
| Suspicious > 5 km | 0 | 0 |
| Suspicious > 10 km | 0 | 0 |

## Count By Merge Reason

| Reason | Legacy count | Corrected importer count |
| --- | --- | --- |
| alias merge | 93 | 107 |
| same coordinates | 4 | 0 |
| near coordinates | 5627 | 0 |
| normalized name match | 8 | 8 |
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
| 1 | near coordinates | 4.998 km | BR | America/Sao_Paulo | 11962401: Cursino / Cursino pop=103171 @ -23.63143,-46.62072 | 1982: Vila Mariana / Vila Mariana pop=12400232 @ -23.58833,-46.63464 | alias intersection: 27, br |
| 2 | near coordinates | 4.997 km | LT | Europe/Vilnius | 8714608: Karoliniškės / Karoliniskes pop=31200 @ 54.69034,25.21903 | 17418: Fabijoniškės / Fabijoniskes pop=37000 @ 54.73333,25.24167 | alias intersection: 65, lt |
| 3 | near coordinates | 4.996 km | IN | Asia/Kolkata | 13353494: Panangad / Panangad pop=15630 @ 10.27284,76.17475 | 13062: Kodungallūr / Kodungallur pop=60190 @ 10.23263,76.19513 | alias intersection: 13, in |
| 4 | near coordinates | 4.994 km | IN | Asia/Kolkata | 13353560: Vilappil / Vilappil pop=36212 @ 8.52218,77.04001 | 14749: Vilavoorkkal / Vilavoorkkal pop=31761 @ 8.48093,77.02204 | alias intersection: 13, in |
| 5 | near coordinates | 4.993 km | ES | Europe/Madrid | 6544493: Carabanchel / Carabanchel pop=253678 @ 40.39094,-3.72420 | 8990: Villaverde / Villaverde pop=141189 @ 40.35000,-3.70000 | alias intersection: 29, es |
| 6 | near coordinates | 4.992 km | FR | Europe/Paris | 3023924: Conflans-Sainte-Honorine / Conflans-Sainte-Honorine pop=36358 @ 49.00158,2.09694 | 9611: Saint-Ouen-l'Aumône / Saint-Ouen-l'Aumone pop=30290 @ 49.04353,2.12134 | alias intersection: 11, fr |
| 7 | near coordinates | 4.992 km | ES | Europe/Madrid | 3126890: Cambre / Cambre pop=23231 @ 43.29438,-8.34736 | 9083: Oleiros / Oleiros pop=35559 @ 43.33333,-8.31667 | alias intersection: 58, es |
| 8 | near coordinates | 4.992 km | NL | Europe/Amsterdam | 2758598: Borne / Borne pop=23877 @ 52.30136,6.74820 | 19487: Hengelo / Hengelo pop=82311 @ 52.26583,6.79306 | alias intersection: 15, nl |
| 9 | near coordinates | 4.992 km | CL | America/Santiago | 3888214: Hacienda La Calera / Hacienda La Calera pop=49106 @ -32.78333,-71.21667 | 4453: La Cruz / La Cruz pop=17310 @ -32.82748,-71.22634 | alias intersection: 01, cl |
| 10 | near coordinates | 4.989 km | KR | Asia/Seoul | 1882056: Sinhyeon / Sinhyeon pop=82560 @ 34.88250,128.62667 | 17132: Kyosai / Kyosai pop=72124 @ 34.85028,128.58861 | alias intersection: 20, kr |
| 11 | near coordinates | 4.988 km | IN | Asia/Kolkata | 13353536: Talikkulam / Talikkulam pop=25507 @ 10.44036,76.09483 | 14732: Karamuck / Karamuck pop=17757 @ 10.48421,76.10445 | alias intersection: 13, in |
| 12 | near coordinates | 4.988 km | UZ | Asia/Tashkent | 1514258: Chortoq / Chortoq pop=53400 @ 41.06924,71.82372 | 27190: Uychi / Uychi pop=29683 @ 41.02900,71.85000 | alias intersection: 06, uz |
| 13 | near coordinates | 4.988 km | US | America/Los_Angeles | 5378771: Oceanside / Oceanside pop=175691 @ 33.19587,-117.37948 | 26511: Carlsbad / Carlsbad pop=114746 @ 33.15809,-117.35059 | alias intersection: ca, us |
| 14 | near coordinates | 4.988 km | HK | Asia/Hong_Kong | 12719443: Wu Kai Sha / Wu Kai Sha pop=23511 @ 22.43016,114.24212 | 10927: Tai Mei Tuk / Tai Mei Tuk pop=17544 @ 22.47447,114.23458 | alias intersection: hk |
| 15 | near coordinates | 4.984 km | CR | America/Costa_Rica | 3621849: San José / San Jose pop=335007 @ 9.93388,-84.08489 | 6853: San Vicente / San Vicente pop=34447 @ 9.96194,-84.04940 | alias intersection: 08, cr |
| 16 | near coordinates | 4.983 km | ES | Europe/Madrid | 6544103: Horta-Guinardó / Horta-Guinardo pop=168092 @ 41.41849,2.16770 | 9038: Santa Coloma de Gramenet / Santa Coloma de Gramenet pop=217741 @ 41.45152,2.20810 | alias intersection: 56, es |
| 17 | near coordinates | 4.983 km | PS | Asia/Gaza | 6967865: Al Qarārah / Al Qararah pop=19500 @ 31.37389,34.34085 | 20969: Khān Yūnis / Khan Yunis pop=173183 @ 31.34018,34.30627 | alias intersection: gz, ps |
| 18 | near coordinates | 4.981 km | US | America/New_York | 5204783: Oxford Circle / Oxford Circle pop=48856 @ 40.05011,-75.07184 | 26296: Bustleton / Bustleton pop=32655 @ 40.08261,-75.03156 | alias intersection: pa, us |
| 19 | near coordinates | 4.981 km | CN | Asia/Shanghai | 1908004: Wenquan / Wenquan pop=18314 @ 34.65193,105.05352 | 5095: Simen / Simen pop=27168 @ 34.62222,105.01278 | alias intersection: 15, cn |
| 20 | near coordinates | 4.980 km | JP | Asia/Tokyo | 10963038: Ōjima / Ojima pop=63254 @ 35.68917,139.83282 | 15958: Sumida / Sumida pop=453093 @ 35.73289,139.82085 | alias intersection: 40, jp |
| 21 | near coordinates | 4.980 km | IN | Asia/Kolkata | 10925345: Chēmanchēri / Chemancheri pop=34819 @ 11.40482,75.72363 | 12349: Koyilandy / Koyilandy pop=71873 @ 11.43810,75.69306 | alias intersection: 13, in |
| 22 | near coordinates | 4.979 km | CN | Asia/Urumqi | 12450868: Tuohula / Tuohula pop=18800 @ 37.24227,79.69283 | 4618: Qaraqash / Qaraqash pop=66541 @ 37.27246,79.73438 | alias intersection: 13, cn |
| 23 | near coordinates | 4.979 km | FI | Europe/Helsinki | 847422: Myyrmäki / Myyrmaeki pop=18393 @ 60.26711,24.84713 | 9449: Pitäjänmäki / Pitaejaenmaeki pop=26414 @ 60.22287,24.86103 | alias intersection: 01, fi |
| 24 | near coordinates | 4.978 km | ES | Europe/Madrid | 11549938: Chopera / Chopera pop=19761 @ 40.39476,-3.69907 | 8990: Villaverde / Villaverde pop=253678 @ 40.35000,-3.70000 | alias intersection: 29, es |
| 25 | near coordinates | 4.976 km | FR | Europe/Paris | 2992404: Montigny-lès-Cormeilles / Montigny-les-Cormeilles pop=17910 @ 48.98201,2.20035 | 9579: Taverny / Taverny pop=27271 @ 49.02542,2.21691 | alias intersection: 11, fr |
| 26 | near coordinates | 4.976 km | SE | Europe/Stockholm | 2707462: Hässelby Villastad / Haesselby Villastad pop=19000 @ 59.38000,17.80867 | 22598: Jakobsberg / Jakobsberg pop=24046 @ 59.42268,17.83508 | alias intersection: 26, se |
| 27 | near coordinates | 4.975 km | DE | Europe/Berlin | 2874455: Mahlsdorf / Mahlsdorf pop=29757 @ 52.50935,13.61373 | 7540: Marzahn / Marzahn pop=111508 @ 52.54525,13.56983 | alias intersection: 16, de |
| 28 | near coordinates | 4.975 km | GB | Europe/London | 2652249: Coulsdon / Coulsdon pop=25530 @ 51.32002,-0.14088 | 9992: Wallington / Wallington pop=72000 @ 51.36404,-0.15368 | alias intersection: eng, gb |
| 29 | near coordinates | 4.974 km | IN | Asia/Kolkata | 13494717: Puzhal / Puzhal pop=31665 @ 13.16475,80.20385 | 12543: Pādiyanallūr / Padiyanallur pop=23819 @ 13.20037,80.17606 | alias intersection: 25, in |
| 30 | near coordinates | 4.973 km | SG | Asia/Singapore | 1882101: Serangoon New Town / Serangoon New Town pop=116900 @ 1.35083,103.87083 | 22626: Yio Chu Kang / Yio Chu Kang pop=87320 @ 1.39111,103.85139 | alias intersection: 00, sg |
| 31 | near coordinates | 4.973 km | SG | Asia/Singapore | 1880469: Marsiling / Marsiling pop=22000 @ 1.43254,103.77407 | 22627: Yew Tee / Yew Tee pop=39100 @ 1.39665,103.74738 | alias intersection: 03, sg |
| 32 | near coordinates | 4.973 km | IT | Europe/Rome | 13607968: Circoiscrizione IV / Circoiscrizione IV pop=98787 @ 45.08125,7.63188 | 15376: Venaria Reale / Venaria Reale pop=50000 @ 45.12597,7.63136 | alias intersection: 12, it |
| 33 | near coordinates | 4.973 km | TW | Asia/Taipei | 1665443: Yuanlin / Yuanlin pop=124725 @ 23.95671,120.57608 | 23851: Yongjing / Yongjing pop=35365 @ 23.92148,120.54594 | alias intersection: 04, tw |
| 34 | near coordinates | 4.972 km | US | Pacific/Honolulu | 13645944: Schofield-Wheeler / Schofield-Wheeler pop=20452 @ 21.48394,-158.04681 | 27056: Mililani Town / Mililani Town pop=27629 @ 21.45040,-158.01503 | alias intersection: hi, us |
| 35 | near coordinates | 4.972 km | RU | Europe/Moscow | 517161: Novyye Cherëmushki / Novyye Cheremushki pop=101000 @ 55.70000,37.58333 | 21323: Zyuzino / Zyuzino pop=121000 @ 55.65608,37.56846 | alias intersection: 48, ru |
| 36 | near coordinates | 4.972 km | BE | Europe/Brussels | 2796542: Harelbeke / Harelbeke pop=25978 @ 50.85343,3.30935 | 937: Zwevegem / Zwevegem pop=23358 @ 50.81268,3.33848 | alias intersection: be, vlg |
| 37 | near coordinates | 4.971 km | CA | America/Toronto | 6183590: Woburn / Woburn pop=53485 @ 43.76657,-79.22773 | 3701: Cliffcrest / Cliffcrest pop=17123 @ 43.72192,-79.23091 | alias intersection: 08, ca |
| 38 | near coordinates | 4.971 km | SR | America/Paramaribo | 8220838: Munder Buiten / Munder Buiten pop=17234 @ 5.84116,-55.18247 | 22819: Flora / Flora pop=19538 @ 5.80000,-55.20000 | alias intersection: 16, sr |
| 39 | near coordinates | 4.969 km | US | America/New_York | 4955840: Wilmington / Wilmington pop=22325 @ 42.54648,-71.17367 | 25815: Burlington / Burlington pop=24498 @ 42.50482,-71.19561 | alias intersection: ma, us |
| 40 | near coordinates | 4.968 km | VE | America/Caracas | 3647549: Cagua / Cagua pop=119033 @ 10.18634,-67.45935 | 27278: Turmero / Turmero pop=344700 @ 10.22856,-67.47421 | alias intersection: 04, ve |
| 41 | near coordinates | 4.968 km | IT | Europe/Rome | 3174679: Lissone / Lissone pop=37353 @ 45.61236,9.23985 | 15423: Seregno / Seregno pop=42760 @ 45.65002,9.20548 | alias intersection: 09, it |
| 42 | near coordinates | 4.967 km | DE | Europe/Berlin | 2936977: Dillingen / Dillingen pop=21526 @ 49.35557,6.72781 | 7351: Saarlouis / Saarlouis pop=38333 @ 49.31366,6.75154 | alias intersection: 09, de |
| 43 | near coordinates | 4.967 km | DE | Europe/Berlin | 2943573: Bruchköbel / Bruchkoebel pop=20509 @ 50.17853,8.92315 | 7730: Hanau am Main / Hanau am Main pop=88648 @ 50.13423,8.91418 | alias intersection: 05, de |
| 44 | near coordinates | 4.967 km | TN | Africa/Tunis | 2473420: Ouardenine / Ouardenine pop=18287 @ 35.70915,10.67397 | 23386: Maatmeur / Maatmeur pop=18996 @ 35.75167,10.69083 | alias intersection: 16, tn |
| 45 | near coordinates | 4.967 km | ZA | Africa/Johannesburg | 12718834: Thubelihle / Thubelihle pop=15876 @ -26.21551,29.29164 | 27891: Kriel / Kriel pop=18255 @ -26.25000,29.26000 | alias intersection: 07, za |
| 46 | near coordinates | 4.966 km | PT | Europe/Lisbon | 2265726: Moscavide e Portela / Moscavide e Portela pop=22488 @ 38.77929,-9.10222 | 21007: São João da Talha / Sao Joao da Talha pop=18925 @ 38.82378,-9.09719 | alias intersection: 14, pt |
| 47 | near coordinates | 4.966 km | CA | America/Toronto | 6137579: Saint-Charles-Borromée / Saint-Charles-Borromee pop=15285 @ 46.05007,-73.46586 | 3754: Joliette / Joliette pop=34772 @ 46.01640,-73.42360 | alias intersection: 10, ca |
| 48 | near coordinates | 4.966 km | DZ | Africa/Algiers | 2491911: Khemis Miliana / Khemis Miliana pop=80512 @ 36.26104,2.22015 | 8252: Miliana / Miliana pop=43366 @ 36.30554,2.22480 | alias intersection: 35, dz |
| 49 | near coordinates | 4.965 km | IN | Asia/Kolkata | 10337414: Singānuram / Singanuram pop=20061 @ 18.82218,79.50171 | 12624: Nāspur / Naspur pop=89935 @ 18.84577,79.46165 | alias intersection: 40, in |
| 50 | near coordinates | 4.965 km | IN | Asia/Kolkata | 11655503: Triparappu / Triparappu pop=22401 @ 8.39479,77.26588 | 12999: Kulasegaram / Kulasegaram pop=17267 @ 8.36319,77.29777 | alias intersection: 25, in |
| 51 | near coordinates | 4.965 km | IN | Asia/Kolkata | 1273618: Daman / Daman pop=44282 @ 20.41431,72.83236 | 13126: Khali Kachigam / Khali Kachigam pop=18434 @ 20.38333,72.86667 | alias intersection: 52, in |
| 52 | near coordinates | 4.964 km | VN | Asia/Ho_Chi_Minh | 8657105: Hòa Cường / Hoa Cuong pop=119363 @ 16.04314,108.18209 | 27608: Da Nang / Da Nang pop=1276000 @ 16.06778,108.22083 | alias intersection: 48, vn |
| 53 | near coordinates | 4.964 km | US | America/New_York | 4504225: South Vineland / South Vineland pop=58122 @ 39.44595,-75.02879 | 25181: Millville / Millville pop=28230 @ 39.40206,-75.03934 | alias intersection: nj, us |
| 54 | near coordinates | 4.963 km | IN | Asia/Kolkata | 11556989: Ālampālaiyam / Alampalaiyam pop=20286 @ 11.36353,77.76773 | 13613: Erode / Erode pop=521891 @ 11.34280,77.72741 | alias intersection: 25, in |
| 55 | near coordinates | 4.962 km | FR | Europe/Paris | 3034610: Paris 17 Batignolles-Monceau / Paris 17 Batignolles-Monceau pop=159212 @ 48.88350,2.32190 | 9559: Paris 15 Vaugirard / Paris 15 Vaugirard pop=229713 @ 48.84120,2.30030 | alias intersection: 11, fr |
| 56 | near coordinates | 4.961 km | BR | America/Sao_Paulo | 11962427: Jardim Sao Luis / Jardim Sao Luis pop=259377 @ -23.68073,-46.73940 | 3534: Jardim Angela / Jardim Angela pop=311432 @ -23.71636,-46.76872 | alias intersection: 27, br |
| 57 | near coordinates | 4.960 km | DE | Europe/Berlin | 2913195: Haan / Haan pop=29431 @ 51.19382,7.01330 | 7441: Ohligs / Ohligs pop=43063 @ 51.15000,7.00000 | alias intersection: 07, de |
| 58 | near coordinates | 4.960 km | SG | Asia/Singapore | 1880650: Hong Kah / Hong Kah pop=26150 @ 1.35944,103.72278 | 22627: Yew Tee / Yew Tee pop=39370 @ 1.39665,103.74738 | alias intersection: 00, sg |
| 59 | near coordinates | 4.959 km | DE | Europe/Berlin | 2949235: Biebrich / Biebrich pop=38758 @ 50.04150,8.24878 | 7152: Wiesbaden / Wiesbaden pop=288850 @ 50.08601,8.24435 | alias intersection: 05, de |
| 60 | near coordinates | 4.959 km | NZ | Pacific/Auckland | 6232009: Otahuhu / Otahuhu pop=17780 @ -36.93820,174.84019 | 19660: Mangere / Mangere pop=28540 @ -36.96807,174.79875 | alias intersection: e7, nz |
| 61 | near coordinates | 4.958 km | AU | Australia/Melbourne | 2161540: Kew / Kew pop=24499 @ -37.80639,145.03086 | 584: South Yarra / South Yarra pop=5350705 @ -37.83834,144.99149 | alias intersection: 07, au |
| 62 | near coordinates | 4.957 km | CA | America/Toronto | 12156824: Banbury-Don Mills / Banbury-Don Mills pop=27695 @ 43.73766,-79.34972 | 3661: Bayview Village / Bayview Village pop=79440 @ 43.77639,-79.38028 | alias intersection: 08, ca |
| 63 | near coordinates | 4.956 km | JP | Asia/Tokyo | 1861212: Iwakuni / Iwakuni pop=129125 @ 34.16297,132.22000 | 16032: Ōtake / Otake pop=30151 @ 34.20754,132.22063 | alias intersection: jp |
| 64 | alias merge | 4.956 km | JP | Asia/Tokyo | 7279570: Higashimurayama / Higashimurayama pop=151815 @ 35.75459,139.46852 | 15902: Tokorozawa / Tokorozawa pop=344194 @ 35.79916,139.46903 | alias intersection: 40, dong cun shan, jp, 東村山 |
| 65 | near coordinates | 4.956 km | US | America/New_York | 5104404: Sayreville / Sayreville pop=44920 @ 40.45927,-74.36098 | 26079: Old Bridge / Old Bridge pop=23753 @ 40.41483,-74.36543 | alias intersection: nj, us |
| 66 | near coordinates | 4.956 km | TH | Asia/Bangkok | 7026842: Pathum Wan / Pathum Wan pop=53263 @ 13.73698,100.52329 | 23087: Yan Nawa / Yan Nawa pop=196129 @ 13.69634,100.54212 | alias intersection: 40, th |
| 67 | near coordinates | 4.955 km | PT | Europe/Lisbon | 2740637: Coimbra / Coimbra pop=140796 @ 40.20686,-8.41996 | 21059: São Paulo de Frades / Sao Paulo de Frades pop=41150 @ 40.24678,-8.39402 | alias intersection: 07, pt |
| 68 | near coordinates | 4.955 km | US | America/Chicago | 4885156: Bloomingdale / Bloomingdale pop=22254 @ 41.95753,-88.08090 | 25577: Glendale Heights / Glendale Heights pop=34208 @ 41.91460,-88.06486 | alias intersection: il, us |
| 69 | near coordinates | 4.954 km | MX | America/Mexico_City | 3530123: Coyotepec / Coyotepec pop=35677 @ 19.77722,-99.21295 | 18194: Teoloyucan / Teoloyucan pop=51255 @ 19.74423,-99.18113 | alias intersection: 15, mx |
| 70 | near coordinates | 4.954 km | NL | Europe/Amsterdam | 2758927: Bilthoven / Bilthoven pop=23248 @ 52.13000,5.20139 | 19369: Zeist / Zeist pop=60949 @ 52.09000,5.23333 | alias intersection: 09, nl |
| 71 | near coordinates | 4.953 km | US | America/New_York | 4354573: Fairland / Fairland pop=23681 @ 39.07622,-76.95775 | 24988: Cloverly / Cloverly pop=15126 @ 39.10816,-76.99775 | alias intersection: md, us |
| 72 | near coordinates | 4.952 km | MY | Asia/Kuala_Lumpur | 7779082: Sri Petaling / Sri Petaling pop=50000 @ 3.06881,101.68971 | 18875: Seri Kembangan / Seri Kembangan pop=130252 @ 3.03333,101.71667 | alias intersection: my |
| 73 | near coordinates | 4.952 km | GM | Africa/Banjul | 12640501: New Jeshwang / New Jeshwang pop=20878 @ 13.44735,-16.66500 | 10669: Welingara / Welingara pop=340000 @ 13.40361,-16.67361 | alias intersection: 01, gm |
| 74 | near coordinates | 4.951 km | RU | Europe/Moscow | 542634: Presnenskiy / Presnenskiy pop=122000 @ 55.75894,37.55816 | 21388: Vorob’yovo / Vorob'yovo pop=130000 @ 55.71667,37.53333 | alias intersection: 48, ru |
| 75 | near coordinates | 4.950 km | MY | Asia/Kuala_Lumpur | 10792382: Putra Heights / Putra Heights pop=60000 @ 2.99361,101.57255 | 18877: Puchong / Puchong pop=375181 @ 3.00000,101.61667 | alias intersection: 12, my |
| 76 | near coordinates | 4.950 km | PE | America/Lima | 3949231: Jacobo Hunter / Jacobo Hunter pop=46092 @ -16.44083,-71.55333 | 19836: Arequipa / Arequipa pop=1195700 @ -16.39899,-71.53747 | alias intersection: 04, pe |
| 77 | near coordinates | 4.949 km | ES | Europe/Madrid | 11549939: Ibiza / Ibiza pop=21492 @ 40.41888,-3.67434 | 9018: Tetuán de las Victorias / Tetuan de las Victorias pop=3255944 @ 40.45975,-3.69750 | alias intersection: 29, es |
| 78 | near coordinates | 4.947 km | JP | Asia/Tokyo | 1858681: Kōtari / Kotari pop=80608 @ 34.92097,135.70547 | 16112: Mukō / Muko pop=56859 @ 34.96545,135.70415 | alias intersection: 22, jp |
| 79 | near coordinates | 4.947 km | FR | Europe/Paris | 3019897: Ermont / Ermont pop=28117 @ 48.99004,2.25804 | 9579: Taverny / Taverny pop=34284 @ 49.02542,2.21691 | alias intersection: 11, fr |
| 80 | near coordinates | 4.947 km | DZ | Africa/Algiers | 2491913: Khemis el Khechna / Khemis el Khechna pop=46965 @ 36.64997,3.33080 | 8234: Ouled Moussa / Ouled Moussa pop=40692 @ 36.68394,3.36661 | alias intersection: 40, dz |
| 81 | near coordinates | 4.946 km | JP | Asia/Tokyo | 1857046: Minoh / Minoh pop=136868 @ 34.82691,135.47057 | 15888: Toyonaka / Toyonaka pop=401558 @ 34.78244,135.46932 | alias intersection: 32, jp |
| 82 | near coordinates | 4.946 km | CA | America/Toronto | 12626157: Parc-Extension / Parc-Extension pop=33800 @ 45.52951,-73.63176 | 3649: Ahuntsic-Cartierville / Ahuntsic-Cartierville pop=438366 @ 45.56667,-73.66667 | alias intersection: 10, ca |
| 83 | near coordinates | 4.946 km | NG | Africa/Lagos | 2328811: Nkpor / Nkpor pop=103733 @ 6.15038,6.83042 | 19116: Onitsha / Onitsha pop=1553000 @ 6.14978,6.78569 | alias intersection: 25, ng |
| 84 | near coordinates | 4.945 km | PH | Asia/Manila | 1725919: Bay / Bay pop=33547 @ 14.18368,121.28554 | 20087: Los Baños / Los Banos pop=117030 @ 14.17025,121.24181 | alias intersection: 40, ph |
| 85 | near coordinates | 4.944 km | MY | Asia/Kuching | 1733440: Putatan / Putatan pop=78340 @ 5.92580,116.06094 | 18731: Donggongon / Donggongon pop=78086 @ 5.90702,116.10146 | alias intersection: 16, my |
| 86 | near coordinates | 4.944 km | GU | Pacific/Guam | 7268049: Mangilao Village / Mangilao Village pop=15191 @ 13.44761,144.80109 | 10908: Tamuning-Tumon-Harmon Village / Tamuning-Tumon-Harmon Village pop=19685 @ 13.48773,144.78138 | alias intersection: gu |
| 87 | near coordinates | 4.943 km | IL | Asia/Jerusalem | 294577: Karmi’el / Karmi'el pop=46252 @ 32.90951,35.29768 | 11621: Sakhnīn / Sakhnin pop=31702 @ 32.86506,35.29771 | alias intersection: 03, il |
| 88 | near coordinates | 4.942 km | ES | Europe/Madrid | 11549978: Comillas / Comillas pop=22721 @ 40.39350,-3.71196 | 8990: Villaverde / Villaverde pop=253678 @ 40.35000,-3.70000 | alias intersection: 29, es |
| 89 | near coordinates | 4.941 km | IN | Asia/Kolkata | 11679729: Ariyānkuppam / Ariyankuppam pop=29808 @ 11.89532,79.80709 | 12388: Puducherry / Puducherry pop=657209 @ 11.93381,79.82979 | alias intersection: 22, in |
| 90 | near coordinates | 4.941 km | IN | Asia/Kolkata | 10628607: Aroor / Aroor pop=39214 @ 9.86940,76.30498 | 14210: Arukutti / Arukutti pop=17944 @ 9.86667,76.35000 | alias intersection: 13, in |
| 91 | near coordinates | 4.939 km | AU | Australia/Melbourne | 7932620: Elwood / Elwood pop=15153 @ -37.88214,144.98215 | 584: South Yarra / South Yarra pop=5350705 @ -37.83834,144.99149 | alias intersection: 07, au |
| 92 | near coordinates | 4.938 km | US | America/New_York | 4159805: Iona / Iona pop=15369 @ 26.52036,-81.96398 | 24645: Cape Coral / Cape Coral pop=175229 @ 26.56285,-81.94953 | alias intersection: fl, us |
| 93 | near coordinates | 4.938 km | GB | Europe/London | 2639265: Rochford / Rochford pop=16739 @ 51.58198,0.70673 | 10052: Southend-on-Sea / Southend-on-Sea pop=295310 @ 51.53782,0.71433 | alias intersection: eng, gb |
| 94 | near coordinates | 4.938 km | VE | America/Caracas | 3645469: Cocorote / Cocorote pop=52803 @ 10.31954,-68.78298 | 27313: San Felipe / San Felipe pop=206270 @ 10.34010,-68.74297 | alias intersection: 22, ve |
| 95 | near coordinates | 4.938 km | SE | Europe/Stockholm | 2725201: Årsta / Arsta pop=16807 @ 59.29780,18.05140 | 22561: Östermalm / OEstermalm pop=36418 @ 59.33879,18.08487 | alias intersection: 26, se |
| 96 | near coordinates | 4.937 km | CA | America/Toronto | 7870919: Niagara / Niagara pop=31180 @ 43.64455,-79.40712 | 3806: Oakwood Village / Oakwood Village pop=2794356 @ 43.68278,-79.43833 | alias intersection: 08, ca |
| 97 | near coordinates | 4.936 km | US | America/Chicago | 4904365: Oak Lawn / Oak Lawn pop=56781 @ 41.71087,-87.75811 | 25661: Alsip / Alsip pop=19346 @ 41.66892,-87.73866 | alias intersection: il, us |
| 98 | near coordinates | 4.936 km | US | America/New_York | 4176318: Valrico / Valrico pop=35545 @ 27.93789,-82.23644 | 24635: Bloomingdale / Bloomingdale pop=22711 @ 27.89364,-82.24037 | alias intersection: fl, us |
| 99 | near coordinates | 4.935 km | GH | Africa/Accra | 2298890: Kumasi / Kumasi pop=2544530 @ 6.68848,-1.62443 | 10591: Tafo / Tafo pop=50457 @ 6.73156,-1.61370 | alias intersection: 02, gh |
| 100 | near coordinates | 4.934 km | UA | Europe/Kyiv | 8519916: Obolon / Obolon pop=239500 @ 50.51320,30.50550 | 24217: Podil / Podil pop=2952301 @ 50.46936,30.51627 | alias intersection: 12, ua |

## Top Examples Grouped By Reason

### alias merge

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 4.956 km | JP | Asia/Tokyo | 7279570: Higashimurayama / Higashimurayama pop=151815 @ 35.75459,139.46852 | 15902: Tokorozawa / Tokorozawa pop=344194 @ 35.79916,139.46903 | alias intersection: 40, dong cun shan, jp, 東村山 |
| 2 | 4.882 km | CA | America/Toronto | 5917781: Cartierville / Cartierville pop=34667 @ 45.53118,-73.70358 | 3649: Ahuntsic-Cartierville / Ahuntsic-Cartierville pop=135336 @ 45.56667,-73.66667 | alias intersection: 10, ca, cartierville |
| 3 | 4.694 km | TH | Asia/Bangkok | 10128831: Phra Nakhon / Phra Nakhon pop=51231 @ 13.76512,100.49864 | 23101: Thon Buri / Thon Buri pop=5104476 @ 13.72500,100.48511 | alias intersection: 40, phra nakhon, th |
| 4 | 4.515 km | IT | Europe/Rome | 13607972: Circoiscrizione VIII / Circoiscrizione VIII pop=134028 @ 45.03789,7.67174 | 15380: Vanchiglia / Vanchiglia pop=847287 @ 45.07140,7.70421 | alias intersection: 12, circoiscrizione vii, it |
| 5 | 4.340 km | TH | Asia/Bangkok | 7504194: Khwaeng Bang Khae / Khwaeng Bang Khae pop=38915 @ 13.69162,100.40448 | 23149: Phasi Charoen / Phasi Charoen pop=193002 @ 13.71466,100.43691 | alias intersection: 40, khwaeng bang khae, th |
| 6 | 4.327 km | BR | America/Sao_Paulo | 3471039: Balneário Camboriú / Balneario Camboriu pop=139155 @ -26.99056,-48.63472 | 3083: Camboriú / Camboriu pop=85105 @ -27.02528,-48.65444 | alias intersection: 26, br, camboriu |
| 7 | 4.273 km | CN | Asia/Shanghai | 8054802: Xilinhot / Xilinhot pop=349953 @ 43.93889,116.07021 | 5983: Xilin Hot / Xilin Hot pop=120965 @ 43.96667,116.03333 | alias intersection: 20, cn, xi lin hao te, xi lin hao te shi, xilin hot, xilinhaote shi, xilinhot, 锡林浩特 |
| 8 | 4.195 km | US | America/New_York | 4955089: West Springfield / West Springfield pop=27912 @ 42.10704,-72.62037 | 25801: Agawam / Agawam pop=154341 @ 42.06954,-72.61481 | alias intersection: ma, spryngpyld, us, ספרינגפילד |
| 9 | 4.107 km | US | America/New_York | 4951788: Springfield / Springfield pop=154341 @ 42.10148,-72.58981 | 25801: Agawam / Agawam pop=28761 @ 42.06954,-72.61481 | alias intersection: agawam, agawome, ma, us |
| 10 | 3.977 km | HU | Europe/Budapest | 11054704: Józsefváros / Jozsefvaros pop=76957 @ 47.48938,19.07292 | 11090: Zugló / Zuglo pop=1001748 @ 47.51758,19.10549 | alias intersection: 05, hu, jozsefvaros |

### same coordinates

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.003 km | PH | Asia/Manila | 1692184: Quiapo / Quiapo pop=32236 @ 14.60000,120.98330 | 19940: Santa Cruz / Santa Cruz pop=126735 @ 14.60000,120.98333 | alias intersection: ncr, ph |
| 2 | 0.000 km | JP | Asia/Tokyo | 2112996: Choshi / Choshi pop=58431 @ 35.73333,140.83333 | 16509: Hasaki / Hasaki pop=39209 @ 35.73333,140.83333 | alias intersection: 04, jp |
| 3 | 0.000 km | JP | Asia/Tokyo | 2130306: Furano / Furano pop=21131 @ 43.35000,142.38333 | 16534: Shimo-furano / Shimo-furano pop=25872 @ 43.35000,142.38333 | alias intersection: 12, jp |
| 4 | 0.000 km | RU | Europe/Moscow | 574675: Bol’shaya Setun’ / Bol'shaya Setun' pop=20000 @ 55.71667,37.41667 | 21524: Setun’ / Setun' pop=147497 @ 55.71667,37.41667 | alias intersection: ru |

### near coordinates

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 4.998 km | BR | America/Sao_Paulo | 11962401: Cursino / Cursino pop=103171 @ -23.63143,-46.62072 | 1982: Vila Mariana / Vila Mariana pop=12400232 @ -23.58833,-46.63464 | alias intersection: 27, br |
| 2 | 4.997 km | LT | Europe/Vilnius | 8714608: Karoliniškės / Karoliniskes pop=31200 @ 54.69034,25.21903 | 17418: Fabijoniškės / Fabijoniskes pop=37000 @ 54.73333,25.24167 | alias intersection: 65, lt |
| 3 | 4.996 km | IN | Asia/Kolkata | 13353494: Panangad / Panangad pop=15630 @ 10.27284,76.17475 | 13062: Kodungallūr / Kodungallur pop=60190 @ 10.23263,76.19513 | alias intersection: 13, in |
| 4 | 4.994 km | IN | Asia/Kolkata | 13353560: Vilappil / Vilappil pop=36212 @ 8.52218,77.04001 | 14749: Vilavoorkkal / Vilavoorkkal pop=31761 @ 8.48093,77.02204 | alias intersection: 13, in |
| 5 | 4.993 km | ES | Europe/Madrid | 6544493: Carabanchel / Carabanchel pop=253678 @ 40.39094,-3.72420 | 8990: Villaverde / Villaverde pop=141189 @ 40.35000,-3.70000 | alias intersection: 29, es |
| 6 | 4.992 km | FR | Europe/Paris | 3023924: Conflans-Sainte-Honorine / Conflans-Sainte-Honorine pop=36358 @ 49.00158,2.09694 | 9611: Saint-Ouen-l'Aumône / Saint-Ouen-l'Aumone pop=30290 @ 49.04353,2.12134 | alias intersection: 11, fr |
| 7 | 4.992 km | ES | Europe/Madrid | 3126890: Cambre / Cambre pop=23231 @ 43.29438,-8.34736 | 9083: Oleiros / Oleiros pop=35559 @ 43.33333,-8.31667 | alias intersection: 58, es |
| 8 | 4.992 km | NL | Europe/Amsterdam | 2758598: Borne / Borne pop=23877 @ 52.30136,6.74820 | 19487: Hengelo / Hengelo pop=82311 @ 52.26583,6.79306 | alias intersection: 15, nl |
| 9 | 4.992 km | CL | America/Santiago | 3888214: Hacienda La Calera / Hacienda La Calera pop=49106 @ -32.78333,-71.21667 | 4453: La Cruz / La Cruz pop=17310 @ -32.82748,-71.22634 | alias intersection: 01, cl |
| 10 | 4.989 km | KR | Asia/Seoul | 1882056: Sinhyeon / Sinhyeon pop=82560 @ 34.88250,128.62667 | 17132: Kyosai / Kyosai pop=72124 @ 34.85028,128.58861 | alias intersection: 20, kr |

### normalized name match

| # | Distance | Country | Timezone | Source GeoNames record | Target City record | Trigger/shared aliases |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 3.429 km | IR | Asia/Tehran | 144795: Ābyek / Abyek pop=60107 @ 36.03993,50.53101 | 15202: Ābyek / Abyek pop=55128 @ 36.06667,50.55000 | alias intersection: abiak, abyek, ir |
| 2 | 2.861 km | MX | America/Mexico_City | 6957079: Benito Juárez / Benito Juarez pop=385439 @ 19.37270,-99.15640 | 18419: Benito Juarez / Benito Juarez pop=355017 @ 19.39840,-99.15766 | alias intersection: 09, benito juarez, mx |
| 3 | 2.439 km | IR | Asia/Tehran | 6861211: Kāshān / Kashan pop=304487 @ 34.00228,51.43879 | 15067: Kashan / Kashan pop=304487 @ 33.98237,51.42769 | alias intersection: 28, ir, kashan, كاشان |
| 4 | 2.072 km | US | America/Chicago | 4736096: Texarkana / Texarkana pop=37280 @ 33.42513,-94.04769 | 24615: Texarkana / Texarkana pop=30353 @ 33.44179,-94.03769 | alias intersection: tegsakaena, teksarkana, tekusakana, texarcana, texarkana, tyksarkana, us, тексаркана |
| 5 | 1.136 km | CL | America/Santiago | 3950116: Cañete / Canete pop=31805 @ -37.80000,-73.38333 | 4488: Cañete / Canete pop=20158 @ -37.80128,-73.39616 | alias intersection: 06, canete, cl |
| 6 | 0.626 km | NP | Asia/Kathmandu | 7963596: Panauti / Panauti pop=46595 @ 27.58466,85.52122 | 19607: Panauti̇̄ / Panauti pop=27602 @ 27.58447,85.51487 | alias intersection: 3, np, panauti |
| 7 | 0.254 km | PH | Asia/Manila | 1727401: Banga / Banga pop=91536 @ 6.42381,124.77603 | 20246: Bañga / Banga pop=58855 @ 6.42389,124.77833 | alias intersection: 12, banga, ph |
| 8 | 0.155 km | US | America/New_York | 4748993: Bristol / Bristol pop=17141 @ 36.59649,-82.18847 | 25297: Bristol / Bristol pop=26666 @ 36.59511,-82.18874 | alias intersection: bristol, brystwl, bu li si tuo er, burisutoru, us, бристол, بريستول, フリストル |

### other

No merge examples for this reason.

## Suspicious Merge Buckets

### Distance > 1 km

| Reason | Count |
| --- | --- |
| alias merge | 72 |
| same coordinates | 0 |
| near coordinates | 5405 |
| normalized name match | 5 |
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

- The legacy run produced 5732 merges. Of these, 105 have a strong name/alias or same-coordinate signal, while 5627 are near-coordinate context-only merges.
- Replaying with the corrected importer produces 115 merges, reducing the merge count by 5617.
- A high count of `near coordinates` merges is evidence that the old deduplication was too aggressive because country/admin aliases made unrelated nearby settlements look related.
- Legitimate translated-name merges, including cases like Addis Ababa/Addis Abeba, should remain in the corrected replay because they share real city aliases.
