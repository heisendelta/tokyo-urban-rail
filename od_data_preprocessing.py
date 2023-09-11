# -*- coding: utf-8 -*-
"""OD Data Preprocessing #2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1z231fEA6AsKkMUDNS8_1Wc5DaWVZK3-h
"""

import os

import pandas as pd
import numpy as np

import pykakasi
import string
import multiprocessing

import system_level

def to_romaji(text, preprocess = "都道府県市町村区"):
    # Text preprocessing
    if preprocess:
        text = ''.join([c for c in text if c not in preprocess])

    to_replace = [('Kakuekiteisha', 'Local'), ('Kaisoku', 'Rapid'), ('Tokyou', 'Tokyo'), ('Taishi', 'Daishi'),
    ('Keiyou (1)', 'Keiyo'), ('Marunouchi (1)', 'Marunouchi'), ('Tokaidou', 'Tokaido'), ('Yuurakucho', 'Yurakucho')]

    kks = pykakasi.kakasi()
    result = kks.convert(text)

    romaji = ' '.join([el['passport'] for el in result]).title().strip()
    for replace_stuff in to_replace:
        romaji = romaji.replace(*replace_stuff)

    if romaji.split()[-1] == 'Hon': # '本線' check
        romaji = ''.join(romaji.split()[:-1]) + ' Main'

    romaji = ''.join([c for c in romaji if c in string.ascii_lowercase + string.ascii_uppercase + ' '])

    return romaji.strip()

train_companies = {
    "東日本旅客鉄道": "JR East",
    "東京地下鉄": "Tokyo Metro",
    "東武鉄道": "Tobu Railway",
    "西武鉄道": "Seibu Railway",
    "京成電鉄": "Keisei Electric Railway",
    "京浜急行電鉄": "Keikyu Corporation",
    # "東京臨海高速鉄道": "Tokyo Waterfront Area Rapid Transit",
    # "東京モノレール": "Tokyo Monorail",
    "小田急電鉄": "Odakyu Electric Railway",
    "相鉄": "Sagami Railway",
    "東急電鉄": "Tokyu Corporation",
    "京王電鉄": "Keio Corporation",
    "東京都交通局": "Toei Subway"
}

def translate_station(station):
    if station in train_companies.keys():
        return train_companies[station]

trip_cols = ['entry',
    'enter_company', 'enter_train_name', 'enter_station_name', 'enter_pref', 'enter_ward', 'enter_time',
    'exit_company', 'exit_train_name', 'exit_station_name', 'exit_pref', 'exit_ward', # Exit time is not a column header
    'time_taken', 'num_people'
]

trip_data = pd.DataFrame(columns=trip_cols)
process, chunk_num = 0, 0

def process_chunk(chunk):
    global process, chunk_num

    aggregate_trip_data = pd.DataFrame(columns=trip_cols)

    print('Chunk process starting')

    for entry, row in chunk.iterrows():
        row_df = pd.DataFrame({
            'entry'               : [entry],
            'enter_train_name'    : [to_romaji(row['【入場】路線名'], preprocess="線")],
            'enter_company'       : [translate_station(row['【入場】事業者名'])],
            'enter_station_name'  : [to_romaji(row['【入場】駅名'], preprocess=False)],
            'enter_pref'          : [to_romaji(row['【入場】都道府県'])],
            'enter_ward'          : [to_romaji(row['【入場】市町村区'])],
            'enter_time'          : [row['【入場】時間帯']],
            'exit_company'        : [translate_station(row['【出場】事業者名'])],
            'exit_train_name'     : [to_romaji(row['【出場】路線名'], preprocess="線")],
            'exit_station_name'   : [to_romaji(row['【出場】駅名'], preprocess=False)],
            'exit_pref'           : [to_romaji(row['【出場】都道府県'])],
            'exit_ward'           : [to_romaji(row['【出場】市町村区'])],
            'time_taken'          : [row['所要時間（５分単位）']],
            'num_people'          : [row['人数']],
        })
        aggregate_trip_data = pd.concat([aggregate_trip_data, row_df], ignore_index=True)

        process += 1
        print(process)

    # aggregate_trip_data.to_pickle(f'pickles/final_chunk_{chunk_num}.pkl')
    # chunk_num += 1

    print('Chunk process completed')

    return aggregate_trip_data

filepath = os.path.join('od_data')
csv_files = sorted([f for f in os.listdir(filepath) if f.endswith('.csv')])

for csv_file in csv_files:
    csv_file = os.path.join(filepath, csv_file)

    print(f'Processing {csv_file}')

    multiprocessing.freeze_support()

    num_cores = multiprocessing.cpu_count()
    chunk_size = 20000

    chunks = pd.read_csv(csv_file, chunksize=chunk_size)
    # chunks_with_index = [(index, chunk) for index, chunk in enumerate(chunks)]

    pool = multiprocessing.Pool(processes=num_cores)
    chunk_trip_data = pool.map(process_chunk, chunks)

    pool.close()
    pool.join()

    # print(trip_data)
    # print(chunk_trip_data)

    # print(type(trip_data))
    # print(type(chunk_trip_data))

    trip_data = pd.concat([trip_data] + chunk_trip_data, ignore_index=True, axis=0)

def load_and_print(filename):
    loaded_df = pd.read_pickle(filename)
    return loaded_df

nodes_df = load_and_print('pickles/tokyo_metro_nodes.pkl')
nodes = [row['station_name'] for _, row in nodes_df.iterrows() if row['fare_gate_data_in']['W'] is not None]

def convert_to_string(text):
    return ''.join([c for c in text if c in string.ascii_letters]).capitalize()

unformatted_nodes = list(map(convert_to_string, nodes))

"""## Matrix Creation"""

correction_dict = {'Meijijinguu Mae': 'Meiji-jingumae',
    'Tameike Sannou': 'Tameike-sanno',
    'Yoyogikoen': 'Yoyogi-koen',
    'Omotesandou': 'Omote-sando',
    'Hiroo': 'Hiro-o',
    'Toyoucho': 'Toyocho',
    'Jinbocho': 'Jimbocho',
    'Azabujuuban': 'Azabu-juban',
    'Akasakamitsuke': 'Akasaka-mitsuke',
    'Higashiginza': 'Higashi-ginza',
    'Yotsuyasanchome': 'Yotsuya-sanchome',
    'Niitaka En Tera': 'Shin-koenji',
    'Shinjukusanchome': 'Shinjuku-sanchome',
    'Hongousanchome': 'Hongo-sanchome',
    'Minamisuna Machi': 'Minami-sunamachi',
    'Minamisenju': 'Minami-senju',
    'Barakinakayama': 'Baraki-nakayama',
    'Zatsu Tsukasa Ga Tani': 'Zoshigaya',
    'Kitasenju': 'Kita-senju',
    'Nakano Sakaue': 'Nakano-sakaue',
    'Hounancho': 'Honancho',
    'Shi Tsu Tani': 'Yotsuya',
    'Nishiwaseda': 'Nishi-waseda',
    'Aoyamaitchome': 'Aoyama-itchome',
    'Shinjukugyoen Mae': 'Shinjuku-gyoemmae',
    'Shin Ochanomizu': 'Shin-ochanomizu',
    'Suitenguumae': 'Suitengumae',
    'Shiroganedai': 'Shirokanedai',
    'Kitaayase': 'Kita-ayase',
    'Hanzoumon': 'Hanzomon',
    'Nakaokachimachi': 'Naka-okachimachi',
    'Nishikasai': 'Nishi-kasai',
    'Roppongi Itchome': 'Roppongi-itchome',
    'Sakurada Mon': 'Sakuradamon',
    'Chikatetsu Narimasu': 'Chikatetsu-narimasu',
    'Higashikoenji': 'Higashi-koenji',
    'Myouden': 'Myoden',
    'Nakano Shimbashi': 'Nakano-shimbashi',
    'Higashi Shinjuku': 'Higashi-shinjuku',
    'Myougadani': 'Myogadani',
    'Toranomon Hiruzu': 'Toranomon Hills',
    'Chikatetsu Akatsuka': 'Chikatetsu-akatsuka',
    'Edogawa Hashi': 'Edogawabashi',
    'Gatsu Shima': 'Tsukishima',
    'Oji Kamiya': 'Oji-kamiya',
    'Kyoubashi': 'Kyobashi',
    'Yu Shima': 'Yushima',
    'Uenohirokoji': 'Ueno-hirokoji',
    'Nishinippori': 'Nishi-nippori',
    'Nakano Fujimicho': 'Nakano-fujimicho',
    'Nishishinjuku': 'Nishi-shinjuku',
    'Minamiyuki Toku': 'Minami-gyotoku',
    'Yukinori': 'Gyotoku',
    'Shinotsuka': 'Shin-otsuka',
    'Kiyosumi Shirakawa': 'Kiyosumi-shirakawa',
    'Monzennakamachi': 'Monzen-nakacho',
    'Kita Sandou': 'Kita-sando',
    'Shinkiba': 'Shin-kiba',
    'Ningyoucho': 'Ningyocho',
    'Nishi Ke Hara': 'Nishigahara',
    'Akabane Iwabuchi': 'Akabane-iwabuchi',
    'Nijuubashimae': 'Nijubashimae',
    'Kotake Mukaihara': 'Kotake-mukaihara',
    'Honkomagome': 'Hon-komagome',
    'Shintomi Machi': 'Shintomicho',
    'Ginzaitchome': 'Ginza-itchome',
    'Hikawa Dai': 'Hikawadai',
    'Minami Asa Ke Tani': 'Minami-Asagaya',
    'Shirogane Takanawa': 'Shirokane-takanawa',
    'San No Wa': 'Minowa',
    'Higashiikebukuro': 'Higashi-ikebukuro',
    'Kokkaigijidoumae': 'Kokkai-gijidomae',
    'Shinchu No': 'Shin-nakano'}
skip_station = ['Wakoshi', 'Nishifunabashi', 'Nakano', 'Nakameguro', 'Meguro', 'Yoyogiuehara']

def try_indexing(station_name):
    global correction_dict, skip_station

    if station_name in skip_station:
        return None

    try:
        origin = nodes.index(station_name)
    except (KeyError, ValueError):
        if station_name in correction_dict.keys():
            origin = nodes.index(correction_dict[station_name])
        else:
            unformat_st_string = convert_to_string(station_name)
            if unformat_st_string in unformatted_nodes:
                corr = nodes[unformatted_nodes.index(unformat_st_string)]
            else:
                corr = input(f'Change {station_name} to >>> ').strip()

            if corr == '':
                skip_station.append(station_name)
                return None

            correction_dict[station_name] = corr
            origin = nodes.index(corr)

    return origin

matrix_list = [np.zeros((138, 138)) for _ in range(24)]

for _, row in trip_data.iterrows():
    enter_time = row['enter_time']
    origin = try_indexing(row['enter_station_name'])
    dest = try_indexing(row['exit_station_name'])

    if origin and dest:
        matrix_list[enter_time - 1][origin, dest] += row['num_people']

print(matrix_list)

np.savez('matrix_list.npz', *matrix_list)