import os
import json
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, HTTPException, Depends
from dotenv import load_dotenv
from glconnect.models import WordsData,db
from sqlalchemy.orm import declarative_base

with open('/etc/glconfig.json') as json_file:
   config=json.load(json_file)

# Load environment variables
db_url = config.get('DB_URL')  

# Set up the database engine and session
engine = create_engine(db_url)  # Using the environment DB_URL
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get the DB session
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize FastAPI
app = FastAPI()


# The dictionary containing your word data
words_data = {
    "kwaba": {
        "umuzi/root": "AAB",
        "basoma/phonetics":{
            " ":"kwaaba",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwaba",
        "icyiciro/pos": ["verb", "inshinga"],
        "igisobanuro/meaning": [
            ["Kunaga amaboko mu byerekezo binyuranye", "agiter les bras en tous sens", "waving the arms in all directions"],
            ["Kuryaryata by’indwara cg ubundi bubabare", "causer des démangeaisons", "sensation that leads a person to scratch"]
        ]
    },
    "umwaba": {
        "umuzi/root": "AAB",
        "basoma/phonetics": {
            " ":"NA",
            "mu buke/singular": "umwaba",
            "mu bwinshi/plural": "imyaba"
        },
        "bandika/writing": "umwaba",
        "icyiciro/pos": ["noun", "izina"],
        "igisobanuro/meaning": [
            "Ibishyimbo cg ibigori bahinga mu bishanga ku mpeshyi.Umugozi bahambiriza uruhu ku muvuba cg ku maseke",
            "Haricots ou maïs cultivés dans les marais pendant la grande saison sèche.Corde dont on se sert pour fixer la peau au soufflet ou aux bâtonnets du soufflet",
            "Beans or maize grown in the marshes during the long dry season.Rope used to attach the skin to the bellows or the rods of the bellows"
        ]
    },
    "cyababo": {
        "umuzi/root": "AAB",
        "basoma/phonetics":
        {   " ":"NA",
            "mu buke/singular": "cyaabaábo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyababo",
        "icyiciro/pos": ["noun", "izina"],
        "igisobanuro/meaning": [
            "Personne trop généreuse",
            "someone too generous"
            "umugwaneza ariko bikabije. sesabayore"
        ]
    },
    "icyabyi": {
        "umuzi/root": "AAB",
        "basoma/phonetics": {
            " ":"NA",
            "ubuke/singular": "icyabyi",
            "ubwinshi/plural": "ibyabyi"
        },
        "bandika/writing": "icyabyi",
        "icyiciro/pos": ["noun", "izina"],
        "igisobanuro/meaning": [
            "uburibwe bw’imikaya",
            "Douleurs puerpérales",
            "postpartum pain"
        ]
    },
     "akabyi": {
        "umuzi/root": "AAB",
        "basoma/phonetics": {
            " ":"NA",
            "ubuke/singular": "akaabyi",
            "ubwinshi/plural": "utwaabyi"
        },
        "bandika/writing": "akabyi",
        "icyiciro/pos": ["noun", "izina"],
        "igisobanuro/meaning": [
            "maternal love",
            "Impuhwe za kibyeyi",
            "Compassion ou amour maternel"
        ]
    },
      "kwabagirana": {
        "umuzi/root": "ÁABAGIRAN",
        "basoma/phonetics": {
            " ":"kwáabagirana",
            "ubuke/singular": "NA",
            "ubuke/plural": "NA"
        },
        "bandika/writing": "kwabagirana",
        "icyiciro/pos": ["verb", "inshinga"],
        "igisobanuro/meaning": [
            "Bellow loudly and at the same time",
            "kwabirira icyarimwe kw'inka",
            "Beugler fort et en même temps"
        ]
    },
    "kwabagiza": {
        "umuzi/root": "ÁABAGIZ",
        "basoma/phonetics": {
            " ":"kwáabagiza",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kwabagiza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            " To call continuously and in an annoying manner",
            " Appeler sans cesse et de façon agaçante",
            " Guhamagara ubutaretsa"
        ]
    },
        "kabakigi": {
        "umuzi/root": " ÁBAKIGÍ ",
        "basoma/phonetics": {
            " ":"kabábakigí",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kabakigi",
        "icyiciro/pos": [
            "izina",
            "noun"
        ],
        "igisobanuro/meaning": [
            " Au jeu de godets, ouverture qui part du cinquième godet à partir de l’extrême droite sur la rangée interne lors du premier mouvement, puis du godet de l’extrême gauche au deuxième mouvement ",
   " Ubwoko bw umuvuno baca bakoze muri gihuhuma ya kabiri bakavunuurira mu mutwe wa kabiri ",
"In the game of cups, the opening starts from the fifth cup from the far right on the inner row during the first movement, then from the cup on the far left during the second movement",

        ]
    },
    "akabarangwe": {
        "umuzi/root": " ÁABARAANGWÉ",
        "basoma/phonetics": {
            " ":"NA",
            " ubuke/singular": " akáabarangwé ",
            " ubwinshi/plural": " utwáabarangwé ",
           
        },
        "bandika/writing": "akabarangwe",
        "icyiciro/pos": [
            "izina",
            "noun"
        ],
        "igisobanuro/meaning": [
            " Ikimenyetso umuntu aba afite ku mubiri, nk’inkovu",
            " Marque indélébile sur la peau humaine, comme une cicatrice",
            "scar"
        ]
    },
    "rwabarasi": {
        "umuzi/root": "ÁABARAASI",
        "basoma/phonetics": {
            " ": "rwáabaraasi",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "rwabarasi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            " hippopotame",
            "imvubu",
            " hippopotamus"
        ]
    },
    "akabarore": {
        "umuzi/root": " ÁABARORÉ ",
        "basoma/phonetics": {
            " ": "akáabaroré",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "akabarore",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "umuntu uhindura amateka ye mabi akagera ku byiza",
            " Répit survenant après une longue période de difficultés",
            " A reprieve occurring after a long period of difficulties"
        ]
    },
    "ubwabazi": {
        "umuzi/root": "ÁABAZI",
        "basoma/phonetics": {
            " ": "ubwáabazi",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "ubwabazi",
        "icyiciro/pos": [
            "izina",
            "noun"
        ],
        "igisobanuro/meaning": [
            "ukubyara kwa mbere k’umuntu cg inka",
            "premier enfantement",
            "first birth"
        ]
    },
    "Kabgayi": {
        "umuzi/root": " AABGÁAYI ",
        "basoma/phonetics": {
            " ": "Kaabgáayi",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "None",
        "icyiciro/pos": [
            "Izina bwite ry’ahantu",
            "noun"
        ],
        "igisobanuro/meaning": [
            "ahantu",
            "lieu",
            "location"
        ]
    },
     "rwabiguma": {
        "umuzi/root": " ÁABIGUMA ",
        "basoma/phonetics": {
            " ": "rwáabiguma",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "rwabiguma",
        "icyiciro/pos": [
            "izina",
            "noun"
        ],
        "igisobanuro/meaning": [
            "umuntu w’indwanyi",
            " Surnom du batailleur ",
            "Nickname given to a warrier"
        ]
    },
    "rwabikobwe": {
        "umuzi/root": " ÁABIKOBWE",
        "basoma/phonetics": {
            " ": "rwáabikobwe",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "rwabikobwe",
        "icyiciro/pos": [
            "izina",
            "noun"
        ],
        "igisobanuro/meaning": [
            "Akazina baha umuntu utazi kubanira abandi",
            "Surnom de l’insociable",
            " Nickname of the unsociable"
        ]
    },
    "cyabingo": {
        "umuzi/root": "ÁABIINGO",
        "basoma/phonetics": {
            " ": "cyáabingo",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "Cyabingo",
        "icyiciro/pos": [
            "Izina bwite",
            "noun"
        ],
        "igisobanuro/meaning": [
            "ahantu",
            "lieu",
            "location"
        ]
    },
    "kwabira": {
        "umuzi/root": "ÁABIR",
        "basoma/phonetics": {
            " ": "kwáabira",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kwabira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            "kuvuga kw’amatungo manini nk’inga cg ihene",
            "beugler",
            "to bellow"
        ]
    },
    "kwabira": {
        "umuzi/root": "AABIIR",
        "basoma/phonetics": {
            " ": "kwaabiira",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kwabira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            "Kurambura amaboko ugasingira ikintu kiri ahitaruye",
            "Étendre les bras pour saisir un objet",
            "stretch out the arms to grab an object"
        ]
    },
        "umwabirizi": {
        "umuzi/root": "AABIRIZI",
        "basoma/phonetics": {
            " ": "umwaabirizi",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "umwabirizi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "Ikibabi by’urushaza",
            "feuille de petit pois",
            "pea leaf"
        ]
    },
    "kwabiza": {
        "umuzi/root": "AABIIRW",
        "basoma/phonetics": {
            " ": "kwáabiza",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kwabiza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            "gutera kwabira",
            "Faire beugler",
            "to make resound"
        ]
    },
    "rwabuduranya": {
        "umuzi/root": "AABUDURÁNYA",
        "basoma/phonetics": {
            " ": "rwaabuduránya",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "rwabuduranya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "izina baha umuntu uhorana inda yujurije",
            "Surnom de qui a le ventre toujours bombé",
            "Nickname for someone who always has a round belly"
        ]
    },
    "rwabuganga": {
        "umuzi/root": "AABUGAANGA",
        "basoma/phonetics": {
            " ": "rwaabugaanga",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "rwabuganga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "ubwoko bw’insina y’ikakama yera igitoki kinini cyane",
            "Variété de bananier à bière, donnant un très gros",
            "Variety of beer banana tree, producing a very large"
        ]
    },
    "rwabugiri": {
        "umuzi/root": "ÁABUGIRI",
        "basoma/phonetics": {
            " ": "Rwáabugiri",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "Rwabugiri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "umwami wa kane w’u Rwanda ushingiye ku bucurabwenge uhabara uhereye inyuma. Izina ry’ubwami ni Kigeri",
            "Le quatrième roi du Rwanda, en comptant à rebours et basé sur la sagesse légendaire. Le nom royal est Rwabugiri",
            "The fourth king of Rwanda, counting backward and based on legendary wisdom. The royal name is Rwabugiri"
        ]
    },
    "kabugomba": {
        "umuzi/root": "ÁABUGOOMBA",
        "basoma/phonetics": {
            " ": "káabugoomba",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kabugomba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "ubwoko bw’igishyimbo",
            "Variété de haricot",
            "Variety of bean"
        ]
    },
    "akabuhembe": {
        "umuzi/root": "AABÚHEEMBE",
        "basoma/phonetics": {
            " ": "akaabúheembe",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "akabuhembe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "gukira icyari hafi yo kuguhitana",
            "sauvetage du dernier instant",
            "the last moment saver"
        ]
    },
    "rwabujune": {
        "umuzi/root": "AABUJUNÉ",
        "basoma/phonetics": {
            " ": "rwaabujuné",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "rwabujune",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "akabyiniriro k’intare",
            "surnom du lion",
            "nickname  given to a lion"
        ]
    },
    "kwabura": {
        "umuzi/root": "AABUUR",
        "basoma/phonetics": {
            " ":"kwaabuura",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kwabura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            "gushahura umuntu ukamaraho",
            "To castrate completely",
            "Châtrer totalement"
        ]
    },
    "rwabusa": {
        "umuzi/root": "RWAABUSA",
        "basoma/phonetics": {
            " ": "rwaabusa",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "rwabusa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "fantaisiste",
            "umuntu ufite ibitekerezo bisa nk’indoto",
            "someone who has whimsical or fantastical ideas, often leaning towards creativity or imagination"
        ]
    },
    "kabushungwe": {
        "umuzi/root": "AABÚSHUUNGWE",
        "basoma/phonetics": {
            " ": "kaabúshungwe",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kabushungwe",
        "icyiciro/pos": [
            "izina",
            "noun"
        ],
        "igisobanuro/meaning": [
            "indakoreka",
            "qui se montre très vaniteux",
            "full of pride and has a sense of superiority"
        ]
    },
    "kabutindi": {
        "umuzi/root": "AABUTIINDI",
        "basoma/phonetics": {
            " ": "kaabutiindi",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kabutindi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "ibyago bigwirira umuntu. Umuntu w'indashyikirwa",
            "Malheur imprévu et fatal.Personne extraordinaire",
            "an unforeseen and fatal disaster. Extraordinary person"
        ]
    },
    "kwaga": {
        "umuzi/root": "ÁAG",
        "basoma/phonetics": {
            " ": "kwáaga",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "kwaga",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            "kuba imfungane kw’ahantu",
            "En parlant d’un espace, être étroit, resserré, exigu",
            "When talking about a space, being narrow"
        ]
    },
    "umwaga": {
        "umuzi/root": "AÁGA",
        "basoma/phonetics": {
            " ": "umwaága",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "umwaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "Imimeréee y’umuntu usa n’urakaye ituma avuga nabi",
            "Dureté, sévérité, acharnement, ardeur, audace",
            " Hardness or emotional toughness"
        ]
    },
    "mwaga": {
        "umuzi/root": "AAGÁ",
        "basoma/phonetics": {
            " ": "mwaagá",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "mwaaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "A Umugezi wo mu Kinyaga usuka mu Kivu hagati ya za komini Gafunzo na Kagano",
            "Rivière de l’Ikinyaga qui se jette dans le lac Kivu, entre les communes de Gafunzo et Kagano",
            "The Ikinyaga River, which flows into Lake Kivu, between the communes of Gafunzo and Kagano"
        ]
    },
    "icyaga": {
        "umuzi/root": "AÁGA",
        "basoma/phonetics": {
            " ": "icyaága",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "icyaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "intwari batigerera",
            "Guerrier vaillant, auquel on n’ose pas se mesurer",
            "A valiant warrior, whom no one dares to challenge"
        ]
    },
    "akaga": {
        "umuzi/root": "AÁGA",
        "basoma/phonetics": {
            " ": "akaága",
            "ubuke/singular": "NA",
            "ubwinshi/plural": "NA"
        },
        "bandika/writing": "akaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "aho umuntu agera ntabe yahikura cg akahikura bimugoye",
            "situation critique",
            "critical situation"
        ]
    },
    "amagaga": {
        "umuzi/root": "áagaagá",
        "basoma/phonetics": {
            " ": "amáagaagá",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amagaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Utunyama two mu nkanka mu imerero ry ururimi","Chair de la région du haut du gosier humain à la base de la langue","Flesh of the region at the top of the human throat at the base of the tongue"
        ]
    },
    "kwagaganya": {
        "umuzi/root": "áagagany",
        "basoma/phonetics": {
            "": "kwáagaganya",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagaganya",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "Gutubya", "Mettre à l’étroit","To confine"
        ]
    },
    
    "kwagagara": {
        "umuzi/root": "áagagar",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagagara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            "Kuba ahantu udafite urwiyaguriro","Être à l’étroit trop serré","To be cramped, too tight"   
        ]
    },
    "kwagagarika": {
        "umuzi/root": "áagagarik",
        "basoma/phonetics": {
            " ": "kwáagagarika",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwáagagarik",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            [
                "Gutsindagirira ibintu ahantu hafunganye", "Pousser mettre à l’étroit","  serrer les uns contre les autres","To press things or people tightly together"
            ]
           
        ]
    },
    "umwagagaro": {
        "umuzi/root": "áagagaro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáagagaro",
            "mu bwinshi/plural": "imyáagagaro"
        },
        "bandika/writing": "umwagagaro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
        
                "Ahantu hafunganye","Lieu exigu","confined space"
        ]
    },
    "kwagagaza": {
        "umuzi/root": "áagagaz",
        "basoma/phonetics": {
            " ": "kwáagagaza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagagaza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gushyira umuntu cg ikintu ahaga","Pousser mettre à l’étroit ou serrer les uns contre les autres","To push, squeeze, or press things or people tightly together"
            
            
        ]
    },
    "rwaagákocó": {
        "umuzi/root": "aagákocó",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaagákocó",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagakoco",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umutego w'imbeba","piège à souris","mouse trap"
            
            
        ]
    },
   
    "kwagamba": {
        "umuzi/root": "áagaamb",
        "basoma/phonetics": {
            " ": "kwáagaamba",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagamba",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutumbagana kw'umuntu cg ikintu kikuzuriza","Enfler se dilater très fort","Swelling, expanding very strongly"
            
        ]
    },
"amagaga": {
        "umuzi/root": "áagaagá",
        "basoma/phonetics": {
            " ": "amáagaagá",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "amáagaagá"
        },
        "bandika/writing": "amagaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Utunyama two mu nkanka mu imerero ry ururimi","Chair de la région du haut du gosier humain à la base de la langue","Flesh of the region at the top of the human throat at the base of the tongue"
        ]
    },
    "kwagaganya": {
        "umuzi/root": "áagagany",
        "basoma/phonetics": {
            "": "kwáagaganya",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagaganya",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "Gutubya", "Mettre à l’étroit","To confine"
        ]
    },
    
    "kwagagara": {
        "umuzi/root": "áagagar",
        "basoma/phonetics": {
            " ": "kwáagagara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagagara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            "Kuba ahantu udafite urwiyaguriro","Être à l’étroit trop serré","To be cramped"   
        ]
    },
    "kwagagarika": {
        "umuzi/root": "áagagarik",
        "basoma/phonetics": {
            " ": "kwáagagarika",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagagarika",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "kugabanya ingano", "Pousser mettre à l’étroit"," to confine"
        ]
    },
    "umwagagaro": {
        "umuzi/root": "áagagaro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáagagaro",
            "mu bwinshi/plural": "imyáagagaro"
        },
        "bandika/writing": "umwagagaro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Ahantu hafunganye","Lieu exigu","Cramped space or tight space"  
        ]
    },
    "kwagagaza": {
        "umuzi/root": "áagagaz",
        "basoma/phonetics": {
            " ": "kwáagagaza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagagaza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "Gushyira umuntu cg ikintu ahaga","Pousser mettre à l’étroit serrer les uns contre les autres","to press tightly against each other"     
        ]
    },
    "rwagakoco": {
        "umuzi/root": "aagákocó",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaagákocó",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagakoco",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umutego w'imbeba","mouse trap","piège à souris"
            
            
        ]
    
    },
    "kwagamba": {
        "umuzi/root": "áagaamb",
        "basoma/phonetics": {
            " ": "kwáagaamba",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagamba",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "Gutumbagana kw' umuntu cg ikintu kikuzuriza","Enfler se dilater très fort","To swell" 
        ]
    },
    "kwagambura": {
        "umuzi/root": "áagaambur",
        "basoma/phonetics": {
            " ": "kwáagaambura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagambura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                " Kuvuga amagambo asa nay'umusazi ahanini bitewe n'ubwoba", "Dire des paroles insensées","To say nonsensical words especially because of fear" 
        ]
    },
    "ikirimarima": {
        "umuzi/root": "rímarim",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ikirímarima",
            "mu bwinshi/plural": "ibirímarima"
        },
        "bandika/writing": "ibirimarima",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikigoryi","idiot","idiot"
            
        ]
    },
    "amagambure": {
        "umuzi/root": "aágaamburé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amaágaamburé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amagambure",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Ibigambo byinshi kandi bidafite icyo bivuga","Longue suite de paroles vides de sens divagation","series of meaningless words"     
        ]
    },
    "kwagana": {
        "umuzi/root": "áagaan",
        "basoma/phonetics": {
            " ": "kwáagaana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "Kuba mu kuba mu mwijima w'ibitekerezo","Être dans un grand embarras","To be in a big dilemma"
        ]
    },
    "icyagane": {
        "umuzi/root": "aágaane",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaágaane",
            "mu bwinshi/plural": "ibyaágaane"
        },
        "bandika/writing": "icyagane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "ibihe bibi cyangwa ibihe biteye inkeke"," Situation fâcheuse","Unfortunate situation"    
        ]
    },
    "kwaganirwa": {
        "umuzi/root": "áagaanirw",
        "basoma/phonetics": {
            " ": "kwáagaanirwa",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwaganirwa",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "Kugira ibyáago by ákajúujuubyo bikakuyobera","Être dans un grand embarras","To be in series of unfortunate situations"
        ]
    },
    "kwaganya": {
        "umuzi/root": "áagany",
        "basoma/phonetics": {
            " ": "kwáaganya",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwaganya",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                 "Kuba úrí haáfi yó gushyikiira icyó wiirúkanye. ", "être sur le point d’atteindre","to be about to reach"  
        ]
    },
    
    "kwagara": {
        "umuzi/root": "aagaar",
        "basoma/phonetics": {
            " ": "kwaagaara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "Guteza uburibwe bukabije","Causer de fortes démangeaisons.","Cause severe itching"
        ]
    },
    "inyagara": {
        "umuzi/root": "agaara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inyagara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "inzara","faim","hunger"  
        ]
    },
    "rwagara": {
        "umuzi/root": "aagaara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Ubwoko bw'icyatsi gifite agati gahagaze kifashishije ibindi kandi kagira udushami twinshi","Herbe à tige subligneuse et sarmenteuse","trailing plant often using tendrils to attach itself to supports"
        ]
        
    },
    "rwagashogoro": {
        "umuzi/root": "aagashogoro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagashogoro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "izina by'igihembwe mu mwaka","nom de season","one of the seasons in a year"
            ]
            
        
    },
    "urwagashya": {
        "umuzi/root": "áagashyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáagashyá",
            "mu bwinshi/plural": "inzáagashyá"
        },
        "bandika/writing": "urwagashya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Inyama yo munda iri hafi y'igifu","the meat in the stomach near the intestines","La viande dans l'estomac près des intestins"
            ]
            
         
        
    },
    "rwaagásurubá": {
        "umuzi/root": "aagásurubá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagásurubá",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "indwanyi kabuhariwe","Terrible batailleur","splendid warrior"
            ]
            
                
            
        
    },
    "umwagati": {
        "umuzi/root": "aágati",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaágati",
            "mu bwinshi/plural": "abaágati"
        },
        "bandika/writing": "umwagati",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            "Umwana uvuka kuu nshuro ya kane","Quatrième enfant dans l’ordre des naissances","fourth child",
            "Umugore umaze kubyara ubwaa kane","Femme qui en est à son quatrième accouchement","women with a fouth birth"
        ]
        
    },
    
    "kwagaza": {
        "umuzi/root": "aagaaz",
        "basoma/phonetics": {
            " ": "kwaagaaza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagaza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                " gushimashima ikintu ushaka ko kiryoherwa","Caresser","To caress" 
        ]
   
    },
    
    "ubwage": {
        "umuzi/root": "aáge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwaáge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwage",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " ubukene bwo kubura ibigutunga bihagíje","Pénurie de vivres","Food shortage"
            
        ]
    },
    
    "umwage": {
        "umuzi/root": "aáge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwaáge",
            "mu bwinshi/plural": "imyaáge"
        },
        "bandika/writing": "umwage",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "NONE","Pers qui cherche refuge surtout auprès d’un parent réfugié.","Person seeking refuge, especially with a refugee relative"
            
        ]
    },
    "amage": {
        "umuzi/root": "aáge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amaáge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amage",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "amaburakindi","dernier recours","Last resort"
            
        ]
    },
    "rwagihanga": {
        "umuzi/root": "aagihaánga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagihanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu cg ikintu gifite umutwe w'ubunini budasanzwe", "Macrocéphale","macrosephalic"    
        ]
    
    },
    "kwagika": {
        "umuzi/root": "áagik",
        "basoma/phonetics": {
            " ": "kwáagika",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagika",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                " Gukenera mu bwage", "mener la vie misérable d’un réfugié.","to lead the miserable life of a refugee."
        ]
    },
    
    "kwagira": {
        "umuzi/root": "áagiir",
        "basoma/phonetics": {
            " ": "kwáagiira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuba ahaga","Se trouver à l’étroit.","to feel cramped"  
        ]
    },
    
    "rwagiriza": {
        "umuzi/root": "aagiriza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaagiriza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagiriza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba intwari ihashya ababisha", "Surnom du vaillant guerrier qui accule l’ennemi.","Nickname of the valiant warrior"
            ]
        
    },
    
    "akagiro": {
        "umuzi/root": "áagiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akáagiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akagiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Umwanya uri mu inguni y'aho urusika ruhuríra n'urundi cg n'inzu","Angle formé par les cloisons de la maison entre elles","Angle formed by the walls of the house with each other"
            ]
        
    },
    "umwagiro": {
        "umuzi/root": "áagiiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáagiiro",
            "mu bwinshi/plural": "umyáagiiro"
        },
        "bandika/writing": "umwagiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ahantu ishyamba rigarukira","Lisière.","edge of a forest"
            
        ]
    },
    "rwagisha": {
        "umuzi/root": "aagísha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaagísha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagisha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu munini kandi w'umugome","Pers robuste et méchante.","A sturdy and wicked person"
            ]
        
    },
    "kagitumba": {
        "umuzi/root": "aagitúumba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaagitúumba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kagitumba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugezi uturuka muri komini Ngarama ugatemba ugana ku mupaka w'urwanda na Uganda ukisuka mu Kagera","Rivière qui prend sa source dans la commune de Ngarama coule en direction de la frontière de l’Ouganda et se jette dans l’Akagera.","A river that originates in the commune of Ngarama flows toward the border of Uganda and empties into the Akagera"
            ]
        
    },
    "icyago": {
        "umuzi/root": "áago",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáago",
            "mu bwinshi/plural": "ibyáago"
        },
        "bandika/writing": "icyago",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ikintu kibi kiba kumuntu kikamuhungabanyiriza ubuzima cg umutekano", "Malheur d’ordre naturel ou surnaturel calamité.","Misfortune of a natural or supernatural order calamity"
            ]
        
    },
    
    
    "kwaguka": {
        "umuzi/root": "áaguk",
        "basoma/phonetics": {
            " ": "kwáaguka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwaguka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuba kigari kw'ikintu cg gushobora kugibwamo n'ibindi bintu byinshi","Être large vaste spacieux.","To be wide"
            ]
        
    },
    "ubwaguke": {
        "umuzi/root": "aáguke",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwaáguke",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwaguke",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuba kigari kw'ikintu cg ugushobora gutwara byinshi","Largeur grande dimension grande capacité.","large dimension"
            ]
        
    },
    "kwagukira": {
        "umuzi/root": "áaguukir",
        "basoma/phonetics": {
            " ": "kwáaguukira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagukira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kugaruka ku cyo wari waranze cg waragaye", "Accepter ou reprendre ce qu’on avait refusé", "To take back what one had refused"
            ]
        
    },
    "icyagumbwa": {
        "umuzi/root": "áaguumbwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáaguumbwá",
            "mu bwinshi/plural": "ibyáaguumbwá"
        },
        "bandika/writing": "icyagumbwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ishaka ritaje ho ihundo","Tige de sorgho stérile.","Sterile sorghum stalk" 
            ]
        
    },
    "kwagura": {
        "umuzi/root": "áagur",
        "basoma/phonetics": {
            " ": "kwáagura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutera ikintu kwaguka","epanouir","expand"
                
            ]
            
                
            
        
    },
    "Kwagura": {
        "umuzi/root": "áagur",
        "basoma/phonetics": {
            " ": "Kwáagura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwagura",
        "icyiciro/pos": [
            "verb",
            "insinga"
        ],
        "igisobanuro/meaning": [
            
                "Kwandura indwarara","Attraper une maladie contagieuse.","to catch a contagious disease."
            ]
            
        
    },
    "rwagusiba": {
        "umuzi/root": "aagusiiba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaagusiiba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwagusiba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "gufata cyari kigiye kugucika","Obtenir ou faire une chose au moment où elle était sur le point d’échapper.","To obtain or do something at the moment it was about to escape"
            ]
        
    },
    "urwagwa": {
        "umuzi/root": "áagwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáagwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwagwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzoga benga mu bitoki","Bière de banane","Banana beer"
            ]
        
        
    },
   
    "kwaha": {
        "umuzi/root": "áah",
        "basoma/phonetics": {
            " ": "kwáaha",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwaha",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gusoroma imboga cg utubuto","Cueillir des légumes ou des fruits.","To gather vegetables or fruits"
            ]
        
    },
    "icyaha": {
        "umuzi/root": "áaha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáaha",
            "mu bwinshi/plural": "ibyáaha"
        },
        "bandika/writing": "icyaha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
             "ikosa ","manquement","Fault"

            ]
        
    },
    "ukwaha": {
        "umuzi/root": "áaha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ukwáaha",
            "mu bwinshi/plural": "amáaha"
        },
        "bandika/writing": "ukwaha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igice cy'umubiri kiri munsi y'urutugu hagati y'imerero ry'ukubuko n'imbavu","Aisselle", "Armpit"
            ]
        
    },
    "kwahagira": {
        "umuzi/root": "aahagir",
        "basoma/phonetics": {
            " ": "kwaahagira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahagira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Guhumeka wungikanya kubera kuzabiranywa","Respirer rapidement ","To breathe quickly" 
            ]
        
    },
    "kwahaguza": {
        "umuzi/root": "áahaguz",
        "basoma/phonetics": {
            " ": "kwáahaguza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahaguza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kurandaguza ibyatsi","Arracher des herbes à plusieurs reprises.","To pull out weeds repeatedly"
            ]
        
    },
    "kwahaha": {
        "umuzi/root": "áahaah",
        "basoma/phonetics": {
            " ": "kwáahaaha",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahaha",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kwirukana umuntu ahantu hose agiye","Chasser de partout persécuter.","To hunt everywhere, to persecute"
            ]
        
    },
    "urwahaha": {
        "umuzi/root": "áahaahá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáahaahá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwahaha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwirukanwa ahantu hose ukajujuta","Fait d’être chassé de partout","persecution that one endures"
            ]
        
    },
    "kwahahana": {
        "umuzi/root": "áahaahan",
        "basoma/phonetics": {
            " ": "kwáahaahana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahahana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": ["Gukorera hamwe mu gutoteza umuntu", "Persécuter ensemble","Persecute together" 
            ]
            
          
    },
    "urwahaho": {
        "umuzi/root": "áahaaho",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáahaaho",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwahaho",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyo umuntu akura ku byo yahashye akagiha undi","Portion d’un achat de vivres offerte en cadeau.","A portion of a food purchase given as a gift" 
            ]
        
    },
    "rwahama": {
        "umuzi/root": "aaháma",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaaháma",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwahama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
        "Ubwoko bw'umuhamirizo,", "style de dance","style of dancing"
        ]

    },
    "abahamagawe": {
        "umuzi/root": "aáhamagawe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "uwaáhamagawe",
            "mu bwinshi/plural": "abaáhamagawe"
        },
        "bandika/writing": "abahamagawe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Abigishwa bo mu cyiciro cya mbere mu nyigisho gatolika","Catéchumènes du premier cycle","Catechumens of the first cycle"
            ]
        
    },
    "irwáahanda": {
        "umuzi/root": "áahaanda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "áahaanda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ahanda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikantarange","Au loin au diable vauvert", "too far, in a distance" 
            ]
        
    },
    "urwahangu": {
        "umuzi/root": "áahaángu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáahaángu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwahangu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuri kwambaye ubusa","Vérité nue","whole truth"
            ]
        
    },
    "kwahanya": {
        "umuzi/root": "aahany",
        "basoma/phonetics": {
            " ": "kwaahanya",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahanya",
        "icyiciro/pos": [
            "verb",
            "ishinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuza vuba n'umurego mwinshi","S’amener en toute hâte.", "To arrive very quickly"
            ]
        
    },
    
    "kahera": {
        "umuzi/root": "aahéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaahéra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kahera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibyago simusiga biba ku muntu","Fatalité qui amène la mort destin funeste.","Fatality that brings death"
            ]
        
    },
    "akahera": {
        "umuzi/root": "áahéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akáahéra",
            "mu bwinshi/prular": "NA"
        },
        "bandika/writing": "akahera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Urusika rw'umusego", "Cloison très petite placée contre la paroi de la maison du côté de la tête du lit","Very small partition placed against the wall of the house on the side of the head of the bed"
            ]
        
    },
    "urwahi": {
        "umuzi/root": "aahi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaahi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwahi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Aho umubyeyi yabyariye", "Lieu où l’on accouche","place where one gives birth."
            ]
    },
            
    "byahi": {
        "umuzi/root": "aahi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "byaahi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "byahi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akarere k'ubugoyi gaherereye mo komini y'umugi ya Rubavu","Région de l’Ubugoyi où se trouve la commune urbaine de Rubavu.","Region of Ubugoyi where the urban municipality of Rubavu is located" 
            ]
        
    },
    "icyahi": {
        "umuzi/root": "aahi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaahi",
            "mu bwinshi/plural": "ibyaahi"
        },
        "bandika/writing": "byahi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "agatambaro bambika uruhinja","diapers","Couches pour bébés",
                "kurya ibyahi ni ugusambana n'umugore wa sobuja cg umuntu ugufiteho ububasha" 
            ]
        
    },
    "iryaahi": {
        "umuzi/root": "aahi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "iryaahi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "iryahi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ubwoko bw'itabi rihingwa mu Byahi", "Variété de tabac cultivée dans la région byahi", "Variety of tobacco grown in the Byahi region" 
            ]
        
    },
    
    "cyahinda": {
        "umuzi/root": "áahiinda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyáahiinda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyahinda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Nyakizu muri perefegitura Butare uriho paruwasi y'abagatorika", "Colline de la commune de Nyakizu dans la préfecture de Butare où est établie une paroisse catholique.","Hill of the Nyakizu municipality in the Butare prefecture where a Catholic parish is established"
            ]
        
    },
    "cyahindiri": {
        "umuzi/root": "aahiindiíri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyaahiindiíri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyahindiri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ukunda gusakuza abuza abandi amahoro","Surnom d’une pers qui se rend importune par sa voix bruyante.","Nickname of a person who becomes annoying due to their loud voice"
            ]
        
    },
    "kwahira": {
        "umuzi/root": "áahir",
        "basoma/phonetics": {
            " ": "kwáahira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [

                " Kurandura cg guca ibyatsi ushikuza", "Arracher des herbes.","Pulling up weeds"
        ]
    },
    "umwahizi": {
        "umuzi/root": "áahizi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáahizi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwahizi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bita impyisi kubera ko iryana ubusambo", "Surnom de l’hyène se référant à sa voracité.", "Nickname of the hyena referring to its voracity"
            ]
        
    },
    "urwaho": {
        "umuzi/root": "áaho",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáaho",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwaho",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "kubona akanya ko gukora ikintu iki n'iki","d’une occasion favorable pour faire qqch.","Take advantage of a favorable opportunity to do something"
            ]
        
    },
    "kwahuka": {
        "umuzi/root": "áahuk",
        "basoma/phonetics": {
            " " :"kwáahuka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahuka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Kuva mu rugo cg mu nama kw' amatungo ajya kurisha","En parlant du bétail quitter l’enclos ou l’aire de repos pour aller paître.","Referring to livestock leaving the enclosure or resting area to go graze"
            
        ]
    },
    "kwahukana": {
        "umuzi/root": "áahukan",
        "basoma/phonetics": {
            " ": "kwáahukana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahukana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gusiga umugabo k'umugore akigira iwabo","En parlant d’une femme quitter son mari de manière temporaire ou définitive.","Referring to a woman leaving her husband temporarily or permanently"
            ]
        
    },
    "kwahukira": {
        "umuzi/root": "áahukiir",
        "basoma/phonetics": {
           "" : "kwahukira ",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahukira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kwitegura gukora ikintu", "Se mettre à faire quelquechose","To start doing something"
            
        ]
    },
    "kwahura": {
        "umuzi/root": "áahur",
        "basoma/phonetics": {
             " ":"kwáahura", 
            "mu buke/singular":"NA",
            "mu bwinshi/plural":"NA"
        },
        "bandika/writing": "kwahura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gukura amatungo mu rugo cg mu nama ukayajyana kurisha", "Emmener le bétail de l’enclos ou de l’aire voisine vers les pâturages.","Take the livestock from the enclosure or the nearby area to the pastures"
            
        ]
    },
    "inyahura": {
        "umuzi/root": "ahúra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inyahúra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inyahura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umurishyo w'ingoma ifite ijwi riranguruye", "Tambour de batterie au son très aigu", "Drum with a very high-pitched sound"
            ]
            
        
    },
    "kwahuranya": {
        "umuzi/root": "áahurany",
        "basoma/phonetics": {
            " ": "kwáahuranya",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwahuranya",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutera ikintu mu kindi kikagicamo kigaseruka ku rundi ruhande","Percer","Pierce through and through"
            ]
        
    },
    "icyahuranyarubanza": {
        "umuzi/root": "áahuranyarúbaánza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáahuranyarúbaánza",
             "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyahuranyarubanza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ijambo rya nyuma rica urubanza rukarangirira aho", "Sentence judiciaire","court ruling"
            ]
        
    },
    "icyahuranyo": {
        "umuzi/root": "áahuranyo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáahuranyo",
            "mu bwinshi/plural": "ibyáahuranyo"
        },
        "bandika/writing": "icyahuranyo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umurongo uciye hagati mu ruziga ukarugabanya mo kabiri","Diamètre","Diameter"
            
        ]
    },
    "umwahuro": {
        "umuzi/root": "áahuro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáahuro",
            "mu bwinshi/plural": "imyáahuro"
        },
        "bandika/writing": "umwahuro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyatsi kiraandaranda kigira metero nyinshi z'uburebure ","Lianes de la famille des Asclépiadacées", "Vines of the Asclepiadaceae family" 
            ] 
        
    },
    "ubwahuro": {
        "umuzi/root": "áahuro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwáahuro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwahuro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikinyobwa kirura kigizwe n'amarwa y'umubira gihabwa ababandwa ubwa mbere bagiherewe mu mutanga bakakinywera kutazamena ibanga","Dans les rites du culte de Ryangombe breuvage amer constitué par de la bière de sorgho incomplètement fermentée","In the rites of the cult of Ryangombe, a bitter beverage made from incompletely fermented sorghum beer"
            ]
        
    },
    
    "ryahuta": {
        "umuzi/root": "áahuuta",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ryáahuuta",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ryahuta",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Irindi zina imandwa zita Ryangombe","nickname for adept of Ryangambe"
            ]
        
    },
    "kwajaba": {
        "umuzi/root": "áajaab",
        "basoma/phonetics": {
            " ": "kwáajaaba",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwajaba",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gusaba ikintu ariko utizeye ko uri bukibone","Demander sans espoir d’obtenir.","To ask without hope of getting"
            ]
        
    },
    "ubwajaba": {
        "umuzi/root": "áajaabá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwáajaabá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwajaba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "kuba ufite uturimo twinshi wirukankamo", "Affairement.", "Business or Affair",
                "Ubuhahara butera umuntu guhora aganya ko akennye kandi ari nta cyo abuze"
            ]
        
    },
    "kajabo": {
        "umuzi/root": "áajabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "káajabo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kajabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba urwagwa kubera ko uwarunyoye atinyuka", "Surnom donné à la bière de banane qui rend une personne audacieux","Nickname given to banana beer because those who drink it become bold."
            ]
        
    },
    "urwaje": {
        "umuzi/root": "aáje",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaáje",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwaje",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Kureka ibiba bikaba kubera ko udashobora kubyigobotora","laisser tomber", "to give in"
            ]
            
    },
    "kwaaka": {
        "umuzi/root": "aak",
        "basoma/phonetics": {
            " ": "kwaaka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwaka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gufata umuriro kwa ikintu bacanye","Prendre feu s’allumer brûler.", "to catch fire"
            ]
    },
    "kwaaka": {
        "umuzi/root": "aak",
        "basoma/phonetics": {
            " ": "kwaaka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwaka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kubwira umuntu kuguha ikintu cg kukimwambura","enlever qqch","to ask for or to take away"
            ]
    },
    "rwaka": {
        "umuzi/root": "aaka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaaka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami w'urwanda utemerwa n'abiru. Izína ry'ubwami ni Karemera","Roi du Rwanda non reconnu par la généalogie officielle et dont le nom de règne est Karemera","Rwandan king who never got official recognition"
            ]
        
    },
    "abaka": {
        "umuzi/root": "aaka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "abaaka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "abaaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "abakomoka mu nzu y'umwami Rwaka","Membres du lignage descendant de Rwaka","Members of the lineage descending from Rwaka"
            ]
        
    },
    
    "umwaka": {
        "umuzi/root": "áaka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáaka",
            "mu bwinshi/plural": "imyáaka"
        },
        "bandika/writing": "umwaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibihingwa byasaruwe","Récolte moisson nourritures agricoles.","Harvest gathers agricultural foods."
            ]
        
    },
    "amaka": {
        "umuzi/root": "áaka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amáaka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Amasaka bahinga muri mutarama bakayasarura muri kamena cg muri nyakanga","Sorgho planté en janvier et récolté en juin juillet.","Sorghum planted in January and harvested in June or July."
            ]
        
    },
    
    "icyaka": {
        "umuzi/root": "aáka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaáka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inyota nyinshi cyane","Soif intense.","Intense thirst."
            ]
        
    },
    "urwaka": {
        "umuzi/root": "aáka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaáka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ububi bw'umurima butera imyaka kubabuka nk'iyatwitswe","Stérilité du sol qui fait mourir les plantes comme si elles étaient brûlées.","Sterility of the soil that causes plants to die as if they were burned."
            ]
    },
    "rwakabaga": {
        "umuzi/root": "aakábaagá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakábaagá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakabaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
               "Izina ry'inzara yabaga yateye mu Rwanda","Famine qui a sévi au Rwanda.","Famine that struck Rwanda."
            ]
        
    },
    "rwakabogeri": {
        "umuzi/root": "aakabogeeri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakabogeeri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakabogeri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'inzara","Nom propre de famine.","Proper name of famine."
            ]
        
    },
    "rwakadogo": {
        "umuzi/root": "aakádoógo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakádoógo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakadogo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akagezi kari hagati ya komini Kayenzi na Taba muri Gitarama kakisuka muri Nyabrongo", "Affluent droit de la Nyabarongo entre les communes de Kayenzi et de Taba dans la préfecture de Gitarama.","Right tributary of the Nyabarongo between the communes of Kayenzi and Taba in the Gitarama prefecture."
            ]
        
    },
    "rwakagara": {
        "umuzi/root": "áakagaara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwáakagaara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakagara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'umwega wari umuhungu wa Gaga", "Personnage du clan Ega qui était fils de Gaga.","Character of the Ega clan who was the son of Gaga."
            ]
        
    },
    "abakagara": {
        "umuzi/root": "áakagaara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáakagaara",
            "mu bwinshi/plural": "abáakagaara"
        },
        "bandika/writing": "abakagara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Abega bo mu muryango ukomoka kuri Rwakagara","Lignage du clan Ega ayant pour ancêtre éponyme Rwakagara.","Lineage of the Ega clan with the eponymous ancestor Rwakagara."
            ]
        
    },
    "icyakaka": {
        "umuzi/root": "aakaaka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaakaaka",
            "mu bwinshi/plural": "ibyaakaaka"
        },
        "bandika/writing": "icyakaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ikintu kibengerana ubwiza kubera ko ari gishya","Objet qui a l’éclat du neuf.","Object that has the shine of newness."
            ]
        
    },
    "kwakakanwa": {
        "umuzi/root": "aakaakanw",
        "basoma/phonetics": {
            " ": "kwaakaakanwa",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakakanwa",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Guhererekanya ikintu kenshi n'abantu benshi","Se passer mutuellement et continuellement qqch.","To pass something to each other mutually and continuously."
            ]
        
    },
    "rwakamigabo": {
        "umuzi/root": "aakamigabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakamigabo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakamigabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba inzara kuko ica intege","Surnom donné à la faim parce qu’elle épuise","Nickname given to hunger because it exhausts."
            ]
        
    },
    "urwakanakana": {
        "umuzi/root": "áakanákana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáakanákana",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwakanakana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Uruhu runagana ku muhogo w'inka","Fanon de vache","Cow's fanon"
            ]
        
    },
    "ibyakanambago": {
        "umuzi/root": "aakanambago",
        "basoma/phonetics": {
            " ": "NA",
      "mu buke/singular": "ibyaakanambago",
     "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibyakanambago",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Abatware b'ibihugu bitandukanye iyo batumvikana","Chefs de pays en conflit", "Leaders of countries in conflict"
            ]
        
    },
    "amakare": {
        "umuzi/root": "aakare",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amaakare",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amakare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Mu gitondo cya kare","Très tôt le matin.","Very early in the morning"
            ]
        
    },
    "icyakatsi": {
        "umuzi/root": "aákaatsi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaákaatsi",
            "mu bwinshi/plural": "ibyaákaatsi"
        },
        "bandika/writing": "icyakatsi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyatsi kidafite umumaro", "Herbe inutilisable.","Unusable grass"
            ]
    
    },
    "rwakayihura": {
        "umuzi/root": "aakayihura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakayihura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakayihura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzara yabaye mu Rwanda ","Famine qui a sévi au Rwanda .","Famine that struck Rwanda."
            ]
        
    },
    "rwakayondo": {
        "umuzi/root": "aakáyoóndo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakáyoóndo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakayondo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzara yabaaye mu Rwanda ", "Famine qui a sévi au Rwanda.", "Famine that afflicted Rwanda."
            ]
        
    },
    "icyake": {
        "umuzi/root": "aáke",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaáke",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyake",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Umugore wahukana akiri ikirongore","Femme qui divorce peu après le mariage.","Woman who divorces shortly after marriage."
            ]
        
    },
    "bwaki": {
        "umuzi/root": "aaki",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bwaaki",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bwaki",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "indwara y'imirire mibi","Kwashiorkor","deficiency in protein"
            ]
        
    },
    "rwakimwaga": {
        "umuzi/root": "aakimwaaga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakimwaaga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakimwaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ukundi bit indyarya"," Pers très rusée"," Very cunning person."
            ]
        
        
    },
    
    "kwakira": {
        "umuzi/root": "aakir",
        "basoma/phonetics": {
            " ": "kwaakira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Guhambiranya imiganda n'igisenge","Assembler les montants et le dôme d’une maison","to assemble the studs and the dome of a house"
            ]
    },
    "kwakira": {
        "umuzi/root": "aakir",
        "basoma/phonetics": {
            " ": "kwaakira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutuma umuntu adakora ikintu ngo arangize","Empêcher qqn de finir une action commencée","to prevent someone from completing an action started"
            ]
    },
    "kwakira": {
        "umuzi/root": "aakiir",
        "basoma/phonetics": {
            " ": "kwaakiira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gufata icyo umuntu aguhereje","Prendre ce qu’on vous tend recevoir en tendant les mains.", "Take what is offered to you by reaching out your hands."
            ]
        
    },
    "kwakira": {
        "umuzi/root": "aakiir",
        "basoma/phonetics": {
            " ": "kwaakiira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gusimbuura ku murimo umuntu wari umaze kunanirwa. ","aider une personne en train de realiser qqch", "to help someone tired in completing tasks"
            ]
        
    },
    "kwakira": {
        "umuzi/root": "aakiir",
        "basoma/phonetics": {
            " ": "kwaakiira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "guha ikaze n'urugwiro abakugana","acceuillir", "welcoming visitors"
            ]
        
    },
    "kwakira": {
        "umuzi/root": "aakiir",
        "basoma/phonetics": {
            " ": "kwaakiira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kubyaza umubyeyi","Assister une parturiente", "to assist in childbirth"
            ]
        
    },
    "kwakira": {
        "umuzi/root": "aakkiir",
        "basoma/phonetics": {
            " ": "kwaakiira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Gukora umuhango wo kwenda umugore wawe kugira ngo icyo wabonye cg watangiye gukora kizaguhire","Accomplir un rite sexuel avec sa femme pour rendre profitable ce que l’on a fait ou reçu","To perform a sexual ritual with one's wife in order to make profitable what has been done or received"
            ]
            
        
    },
    "amakira": {
        "umuzi/root": "aakira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amaakira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amakira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akavura kadafashije karimo izuba","Pluie fine accompagnée de rayons de soleil.","Light rain accompanied by sunshine."
            ]
        
    },
    "ukwakira": {
        "umuzi/root": "aakira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ukwaakira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ukwakira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwezi kwa kabiri k'umwaka wa kinyarwanda","Deuxieme mois l’année rwandaise","second month of the rwandan year",
                "Ukwezi kwa cumi k'umwaka usanzwe","Dixieme mois l’année ordinaire","tenth month of the year"
            ]
        
    },
    "bwakira": {
        "umuzi/root": "aakiira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bwaakiira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bwakira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Umusozi wo muri perefegitura ya Kibuye wahaye izina komini uri mo", "Colline et commune de la préfecture de Kibuye","Hill and commune of the Kibuye prefecture."
           ]
        
    },
    "kwakirana": {
        "umuzi/root": "aakiran",
        "basoma/phonetics": {
            " ": "kwaakirana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakirana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "kubengerana","très brillant","very bright"
            ]
        
    },
    "kwakirira": {
        "umuzi/root": "aakiirir",
        "basoma/phonetics": {
            " ": "kwaakiirira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakirira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Iyo inka zihumuje guhereza abantu bari aho icyansi cy'amata bagakora ho by'umuhango","Après avoir trait les vaches tendre le pot à lait aux pers présentes pour qu’elles le touchent rituellement.","After milking the cows, offer the milk pot to the people present so that they can touch it ritually."
            ]
        
    },
    "icyakiro": {
        "umuzi/root": "aakiiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaakiiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyakiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzoga ihembwa abakozi bakiriye abandi mu mirimo", "Lors d’un travail rémunéré en boisson part qu’on donne aux gens qui sans être invités au préalable relaient ceux qui l’ont été.", "During a paid work with drink that is given to people who, without being invited beforehand, take the place of those who were invited."
            ]
        
    },
    "rwakiziko": {
        "umuzi/root": "aakíziiko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaakíziiko",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwakiziko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzara yabaye mu Rwanda","Nom d’une famine dont on ne peut préciser la date.","Name of a famine for which the date cannot be specified."
            ]
        
    },
    "umwaku": {
        "umuzi/root": "aáku",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaáku",
            "mu bwinshi/plural": "imyaáku"
        },
        "bandika/writing": "umwaku",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amahirwe make cg ibyago","malchance","unluck"
            ]
            
        
    },
    "ubwaku": {
        "umuzi/root": "aáku",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwaáku",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwaku",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inuko y'umubiri w'umuntu cg w'inyamaswa imuranga ", "Odeur propre à une personne ou un animal qui permet de l’identifier","Odor specific to a person or an animal that allows for identification"
                
            ]
        
    },
    "kwakukwa": {
        "umuzi/root": "aakukw",
        "basoma/phonetics": {
            " ": "kwaakukwa",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakukwa",
        "icyiciro/pos": [
            "verbv",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Kuzwaho n'ubuheri", "Attraper une éruption cutanée.","To catch a rash."
            ]
        
    },
    
    "kwakura": {
        "umuzi/root": "aakur",
        "basoma/phonetics": {
            " ": "kwaakura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuvugisha umuntu", "Parler à qqn.","To speak to someone"
            ]
        
    },
    "kwakuranwa": {
        "umuzi/root": "aakuranw",
        "basoma/phonetics": {
            " ": "kwaakuranwa",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakuranwa",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gutwara cg gukora ikintu abantu bagenda bakirana","Se relayer pour transporter une charge ou pour accomplir une tâche quelconque.","To take turns carrying a load or completing any task."
            ]
        
    },
    "kwakuza": {
        "umuzi/root": "aakuz",
        "basoma/phonetics": {
            " ": "kwaakuza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwakuza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "guhamagara"," Appeler","To call"
            ]
            
       
        
    },
    "urwakwaha": {
        "umuzi/root": "áakwaahá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwáakwaahá",
            "mu bwinshi/plural": "ubwáakwaahá"
        },
        "bandika/writing": "urwakwaha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoya bwo mu kwaha", "Poils de l’aisselle.","Underarm hair"
            ]
        
    },
    "urwakwe": {
        "umuzi/root": "aakwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaakwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwakwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Kuvugisha umuntu","Parler à qqn","To talk to someone"
            ]
        
    },
    "kwama": {
        "umuzi/root": "áam",
        "basoma/phonetics": {
            " ": "kwáama",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwama",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
               "kuba ikimenyabose"," Être célèbre","To be famous"
            ]
        
        
    },
    "umwama": {
        "umuzi/root": "aáma",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaáma",
            "mu bwinshi/plural": "imyaáma"
        },
        "bandika/writing": "umwama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwabirana umunihiro kw'imfizi cg ukwivovota kw'intare","Mugissement du taureau ou rugissement du lion.","Bellowing of the bull or roaring of the lion."
            ]
        
    },
    "imyama": {
        "umuzi/root": "aáma",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaáma",
            "mu bwinshi/plural": "imyaáma"
        },
        "bandika/writing": "imyama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Uburyo bwo kuririmbira inka abantu bakuranwa", "Espèce de chant pastoral exécuté par deux groupes en alternance.","A type of pastoral song performed by two groups in alternation."
            ]
        
    },
    
    "kwamagana": {
        "umuzi/root": "áamagan",
        "basoma/phonetics": {
            " ": "kwáamagana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamagana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Guhinda umuntu usakuza cg kumuburiza kure kukwegera", "denoncer","To denounce"
            ]
        
    },
    "rwamagana": {
        "umuzi/root": "áamagana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwáamagana",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamagana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Rutonde wahaye izina superefegitura uri mo","Colline de la commune de Rutonde et sous-préfecture comprenant les communes de Muhazi, Rutonde, Kayonza et Rukara","Hill of the Rutonde commune and sub-prefecture comprising the communes of Muhazi, Rutonde, Kayonza, and Rukara"
            ]
        
    },
    "kamagata": {
        "umuzi/root": "aamágata",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamágata",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamagata",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Intangiriro y'umuhindo","Début de la petite saison des pluies", "Start of the short rainy season"
            ]
        
    },
    "kwamagira": {
        "umuzi/root": "áamagir",
        "basoma/phonetics": {
            " ": "kwáamagira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamagira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kwamagana uvuza induru","Chasser par des cris","to chase away with shout"
            ]
    },
    "kwamagira": {
        "umuzi/root": "áamagir",
        "basoma/phonetics": {
            " ": "kwáamagira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamagira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gukerega imisozi wihuta","Marcher à toute allure et couvrir une grande distance.","to walk at full speed and cover a great distance."
            ]
    },
    "kwamaguza": {
        "umuzi/root": "áamaguz",
        "basoma/phonetics": {
            " ": "kwáamaguza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamaguza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gukubuza muu nzira wihuta", "Marcher à pas pressés", "To walk hurriedly"
            ]
        
    },
    "umwamaguzo": {
        "umuzi/root": "áamaguzo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáamaguzo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwamaguzo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Gukamana ubwira","Traire avec ardeur.","To milk eagerly."
            ]
        
    },
    "rwamahe": {
        "umuzi/root": "aamahé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamahé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamahe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuhungu w'umwami Rujugira wakomotswe ho n'inzu y 'abamahe", "Fils du roi Rujugira qui est devenu l’ancêtre éponyme du sous lignage Abamahe.","Son of King Rujugira who became the eponymous ancestor of the Abamahe sub-lineage."
            ]
        
    },
    "rwamakombe": {
        "umuzi/root": "áamakoombe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwáamakoombe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamakombe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ingabo ihorana ihirwe ryo kwica ku rugamba", "Guerrier qui a toujours la chance de tuer les ennemis au combat.","Warrior who always has the chance to kill enemies in battle."
            ]
        
    },
    "kwamama": {
        "umuzi/root": "áamaam",
        "basoma/phonetics": {
            " ": "kwáamaama",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Gushakira ikintu imihanda yose ugaheba", "Chercher partout mais sans succès", "To search everywhere but without success."
            ]
        
    },
    "kamamanzi": {
        "umuzi/root": "áamamaanzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "káamamaanzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamamanzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'ikijumba", "Variété de patate douce","Variety of sweet potato."
            ]
        
    },
    "kwamamara": {
        "umuzi/root": "áamamar",
        "basoma/phonetics": {
            " ": "kwáamamara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamamara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kumenyekana cyane ukaba ikirangirire", "Être célèbre", "to be famous"
            ]
        
    },
    "rwamamara": {
        "umuzi/root": "aamamara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamamara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamamara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'igihaza","Variété de courge","Variety of squash"
            ]
        
    },
    "icyamamare": {
        "umuzi/root": "aámamare",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaámamare",
            "mu bwinshi/plural": "ibyaámamare"
        },
        "bandika/writing": "icyamamare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Umuntu uzwi ahantu henshi","Personne célèbre","famous person"]
        
    },
    "kwamamaza": {
        "umuzi/root": "áamamaz",
        "basoma/phonetics": {
            " ": "kwáamamaza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamamaza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gukwiza inkuru aho ugenda hose cg kugenda urata umuntu cg ikintu", "Faire connaître répandre une nouvelle,marchandise partout","To advertize"
            ]
        
    },
    "kwamanga": {
        "umuzi/root": "áamaang",
        "basoma/phonetics": {
            " ": "kwáamaanga",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamanga",
        "icyiciro/pos": [
            "verb",
            "ishinga"
        ],
        "igisobanuro/meaning": [
            
                " Kurira ugahogora","S’égosiller en pleurant.","To scream while crying."
            ]
        
    },
    "umwamango": {
        "umuzi/root": "áamaango",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáamaango",
            "mu bwinshi/plural": "imyáamaango"
        },
        "bandika/writing": "umwamango",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umurima munini","Champ très vaste","vast field"
            ]
            
        
    },
    "kamara": {
        "umuzi/root": "aamará",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamará",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu cya ngombwa", "Chose indispensable","essential thing"
            ]
        
    },
    "kamarungu": {
        "umuzi/root": "áamaruungu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "káamaruungu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamarungu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'amasaka","Variété de sorgho.","Variety of sorghum."
            ]
        
    },
    "inamarusaku": {
        "umuzi/root": "ámarusakú",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inámarusakú",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inamarusaku",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu uboroga","Personne criarde","Screaming person"
            ]
        
    },
    "rwamasunzu": {
        "umuzi/root": "áamasuunzu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwáamasuunzu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamasunzu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu ufite amasunzu maremare cyane", "Surnom d’une pers dont les houppes sont très hautes","Nickname of a person with tall tufts"
            ]
        
    },
    "cyamatare": {
        "umuzi/root": "aamatáre",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyaamatáre",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyamatare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami wa cumi na batanu w'urwanda ushingiye ku bucurabwenge ukabara usubira inyuma","Quinzième roi du Rwanda selon la généalogie officielle en comptant à reculons. Son nom de règne est Ndahiro","Fifteenth king of Rwanda according to the official genealogy when counted backwards. His regnal name is Ndahiro"
            ]
        
    },
    "kamatsibage": {
        "umuzi/root": "aamatsibáge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamatsibáge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamatsibage",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'ikijumba","Variété de patate douce","Variety of sweet potato"
            ]
        
    },
    
    "rwamba": {
        "umuzi/root": "aamba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ikimera cyurira ibindi cyo mu karere ka Cyangugu gifite ibibabi byihariye bidasharuye n'indabyo zera ziremye agacuki zimwe zikaza ku nkondo imwe","NONE","NONE"
            ]
        
        
    },
    "mwamba": {
        "umuzi/root": "aámba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mwaámba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mwamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inkingi y'inzu batera ho ingiga y'igiti bashorera ho amaburiti","Pilier central d’une maison en pisé à partir duquel partent les chevrons du toit.","Central pillar of a rammed earth house from which the roof rafters extend."
            ]
        
    },
    "urwamba": {
        "umuzi/root": "aámba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaámbaA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amaraso y'inka benga bakayakura mo imiregesho bakayanywa avanze n'umufa ushyushye cyane","Sang frais d’un animal brassé et filtré qu’on boit mélangé à du jus de viande chaud.","Fresh blood of an animal that is brewed and filtered, which is drunk mixed with hot meat juice."
            ]
        
    },
    "kwambara": {
        "umuzi/root": "aambar",
        "basoma/phonetics": {
            " ": "kwaambara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gushyira cg kugira ku mubiri ikintu cyabugenewe ugira ngo wikinge wikingire wivure cg witake", "se vêtir","to be dressed"
            ]
        
    },
    "umwari": {
        "umuzi/root": "aambari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaambari",
            "mu bwinshi/plural": "abaambari"
        },
        "bandika/writing": "umwambari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugaragu ugendana na shebuja","Serviteur qui accompagne son maître dans ses déplacements","Servant who accompanies his master on his travels"
            ]
        
    },

    "akambarabatabazi": {
        "umuzi/root": "aambarabatabaazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akaambarabatabaazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akambarabatabazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ibyatsi abagore bambara mo impumbya","Herbes que les femmes cueillent pour assurer le succès et le retour triomphal de leur mari parti en guerre", "Herbs that women gather traditionally to ensure the triumphant return of their husbands who have gone to war"
            ]
        
    },
    "kwambarana": {
        "umuzi/root": "aambaran",
        "basoma/phonetics": {
            " ": "kwaambarana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambarana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutiririkanya imyambaro", "Se prêter mutuellement des habits.", "To lend each other clothes."
            ]
        
    },
    "kwambaranya": {
        "umuzi/root": "aambarany",
        "basoma/phonetics": {
            " ": "kwaambaranya",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambaranya",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuba umuntu yitegura gutangira gukora iki n'iki","Faire les préparatifs.", "To make preparations."
             ]
        
    },
    "umwambararuhago": {
        "umuzi/root": "aambararuhago",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaambararuhago",
            "mu bwinshi/plural": "Abaambararuhago"
        },
        "bandika/writing": "umwambararuhago",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umugaragu ugendana na shebuja amutwaje uruhago rw'itabi", "Serviteur qui escorte son maître et porte sa blague à tabac", "Servant who escorts his master and carries his tobacco pouch"
            ]
        
    },
    "umwambari": {
        "umuzi/root": "aambari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaambari",
            "mu bwinshi/plural": "abaambari"
        },
        "bandika/writing": "umwambari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugaragu ugendana na shebuja","Serviteur qui accompagne son maître dans ses déplacements.","Servant who accompanies his master in his travels"
            ]
        
    },
    "rwambari": {
        "umuzi/root": "aambari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwambari",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwambari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umutsobe wakomotsweho n'umuryango wamwitiriwe","Membre du clan Tsobe ancêtre éponyme d’un lignage.", "Member of the Tsobe clan, the eponymous ancestor of a lineage."
            ]
        
    },
    "abambari": {
        "umuzi/root": "aambari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwambari",
            "mu bwinshi/plural": "abambaari"
        },
        "bandika/writing": "abambari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Abatsobe bo mu muryango ukomoka mu nzu yo kwa Rwambari", "Lignage du clan Tsobe ayant Rwambari pour ancêtre éponyme.","Lineage of the Tsobe clan with Rwambari as the eponymous ancestor."
            ]
        
    },
    "kwambarira": {
        "umuzi/root": "aambarir",
        "basoma/phonetics": {
            " ": "kwaambarira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambarira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuba witeguye gukora ikintu","Être prêt disposé à agir.", "To be ready and willing to act."
            ]
        
    },
    "urwambariro": {
        "umuzi/root": "aambariro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaambariro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwambariro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita ubujyana bw ukuboko cg bw ukuguru kubera k bahambarira ibitare ubutega imiringa cg ingoro", "Nom du poignet ou de la cheville se référant au fait qu’on y porte des.","Name for the wrist or ankle referring to the fact that one wears [something] there."
            ]
        
    },
    "umwambaro": {
        "umuzi/root": "aambaro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaambaro",
            "mu bwinshi/plural": "imyaambaro"
        },
        "bandika/writing": "umwambaro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyo umuntu yambara","Vêtement ou tout objet porté sur le corps dans le sens défini pour aambar A.","Clothing or any object worn on the body in the sense defined for aambar A."
            ]
    
    },
    "ibyambarwa": {
        "umuzi/root": "aámbarwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ibyaámbarwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibyambarwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "imyambaro","Vêtements","clothes"
            ]
    },
    "kwambaza": {
        "umuzi/root": "aambaz",
        "basoma/phonetics": {
            " ": "kwaambaza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambaza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutakambira umuntu cg umuzimu ukabikora ushishikaye kugira ngo bigire icyo bigutabaza", "Invoquer prier supplier avec insistance un homme ou un esprit afin d’obtenir une faveur.","To invoke, pray, or earnestly beseech a man or a spirit in order to obtain a favor."
            ]
        
    },
    
    "urwambere": {
        "umuzi/root": "aambere",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaambere",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwambere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igice cya kabiri cy'abigishwa","Deuxième stade du catéchuménat.","Second stage of the catechumenate."
            ]
        
    },
    "amambere": {
        "umuzi/root": "áamberé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amáamberé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amambere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igihe cyashize","A un moment du passé la fois passée dernièrement.","At a moment in the past, the last time."
            ]
        
    },
    "kambere": {
        "umuzi/root": "aamberé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamberé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kambere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzu y'ingenzi mu mazu y'umwami cg y'umuntu ukomeye ari mu rugo rumwe itegeranye n'irembo", "Maison principale dans l’enclos du roi ou d’un grand personnage.","Main house within the enclosure of the king or a great figure."
            ]
        
    },
    "ikambere": {
        "umuzi/root": "áamberé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ikáamberé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ikambere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Mu nzu y'ibanze umwami cg undi umuntu ukomeye arara mo", "Dans la maison principale du roi ou d’un grand personnage.","In the main house of the king or a great figure."
            ]
        
    },
    "umwambi": {
        "umuzi/root": "aambi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaambi",
            "mu bwinshi/plural": "imyaambi"
        },
        "bandika/writing": "umwambi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akuma bakwikira mu ibano bakakarashisha","Fer de flèche.","Arrowhead."
            ]
        
    },
    
    "myambi": {
        "umuzi/root": "aambi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "myaambi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "myambi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "indwara yo gucibwamo","dysenterie","dysentery"
            ]
        
    },
    
    "kwambika": {
        "umuzi/root": "aambik",
        "basoma/phonetics": {
            " ": "kwaambika",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambika",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gushyira ikintu cg umuntu ho umwambaro cg kuwumuha","habiller","to dress"
            ]
        
    },
    "kwambikana": {
        "umuzi/root": "aambikan",
        "basoma/phonetics": {
            " ": "kwaambikana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambikana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                 "Gutangira gutongana cg kurwana","Commencer à se quereller ou à se battre.","To start quarreling or fighting."
        
            ]
        
    },
    "iynambike": {
        "umuzi/root": "ambíke",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "iynambíke",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "iynambike",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'igitoki","Bananier","Banana tree"
             ]
        
    },
    "kwambikira": {
        "umuzi/root": "aambikir",
        "basoma/phonetics": {
            " ": "kwaambikira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambikira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kuba witeguye", "Être prêt à","to be ready to"
            ]
            
        
    },
    "urwambikiro": {
        "umuzi/root": "aambikiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaambikiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwambikiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubuniga bw'isuka y'Inyarwanda buhuza imbaba n'umusa","Partie du fer de la houe traditionnelle faisant jonction entre le plat et la soie", "Part of the iron of the traditional hoe connecting the blade and the handle."
            ]
        
    },
    "icyambiko": {
        "umuzi/root": "aambiko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaambiko",
            "mu bwinshi/plural": "ibyaambiko"
        },
        "bandika/writing": "icyambiko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "urukenyerero", "taille","waist"
            ]
            
    },
    "umwambiro": {
        "umuzi/root": "aambiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaambiro",
            "mu bwinshi/plural": "imyaambiro"
        },
        "bandika/writing": "umwambiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umusemburo w'imigati","Levure","yeast"
            ]
            
                
            
        
    },
    "mwambiya": {
        "umuzi/root": "aambiyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mwaambiyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mwambiya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'umwumbati", "Variété de manioc","Variety of cassava"
            ]
        
    },
    "icyambo": {
        "umuzi/root": "aambo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaambo",
            "mu bwinshi/plural": "ibyaambo"
        },
        "bandika/writing": "icyambo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Agakoko bashyira ku ndobani barobesha kakareshya amafi","Appât mis à l’hameçon.","Bait put on the hook"
            ]
        
    },
    "ibyambo": {
        "umuzi/root": "aambo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ibyaambo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibyambo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "amahirwe","chance","luck"
            ]
        
        
    },
    "akambonwa": {
        "umuzi/root": "áambonwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akáambonwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akambonwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukubonwa ukora ikintu wakekaga ko wihishanye", "Fait d’être vu alors qu’on croyait agir secrètement flagrant délit.", "The act of being seen while believing to act secretly."
            ]
        
    },
    "Icyambu": {
        "umuzi/root": "aámbu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "Icyaámbu",
            "mu bwinshi/plural": "Ibyaámbu"
        },
        "bandika/writing": "Icyambu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ahantu baca bambuka, umugezi ikiyaga cg igishanga kwaba kugenda ku maguru, mu bwato cg banyuze ku kiraro","Lieu où l’on traverse un cours d’eau un lac un marais etc à gué en pirogue ou sur un pont point de passage.","Place where one crosses a watercourse, a lake, a marsh, etc. by wading, in a canoe, or on a bridge; crossing point."
            ]
        
    },
    
    "icyambu": {
        "umuzi/root": "aámbu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaámbu",
            "mu bwinshi/plural": "ibyaámbu"
        },
        "bandika/writing": "icyambu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ahantu baca bambuka umugezi","Lieu où l’on traverse un cours d’eau, un lac","port"
            ]
        
    },
    "akambuguyu": {
        "umuzi/root": "aambuguyu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akaambuguyu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akambuguyu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "akayihayiho","Forte envie","strong craving"
            ]
        
    },
    "kwambuka": {
        "umuzi/root": "aambuk",
        "basoma/phonetics": {
            " ": "kwaambuka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambuka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuva ku musozi ugafata undi uciye mu mazi cg mu gishanga cg ku kiraro", "Traverser un cours d’eau un lac ou un marais à gué en pirogue ou sur un pont.","To cross a watercourse, a lake, or a marsh by wading, in a canoe, or on a bridge."
            ]
        
    },
    
    "inyambukamugezi": {
        "umuzi/root": "ambukamugezi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inyambukamugezi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inyambukamugezi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu cg itungo bituruka ahandi","Étranger pers ou animal domestique venus d’ailleurs.","Foreign person or domestic animal that has come from elsewhere."
            ]
        
    },
    "umwambukira": {
        "umuzi/root": "áambukiirá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáambukiirá",
            "mu bwinshi/plural": "abáambukiirá"
        },
        "bandika/writing": "umwambukira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umunyamahanga","etranger","foreigner"
            ]
        
    },
    "kwambukiranya": {
        "umuzi/root": "aambukirany",
        "basoma/phonetics": {
            " ": "kwaambukiranya",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambukiranya",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "guhinguranya"," Traverser d’un bout à l’autre","To cross from one end to the other"
            ]
            
         
    },
    "kwambukirwa": {
        "umuzi/root": "aambukirw",
        "basoma/phonetics": {
            " ": "kwaambukirwa",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambukirwa",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gucikwa n'imyambaro ukambara ubusa","Laisser voir sa nudité son sexe par inadvertance.","To inadvertently expose one's nudity or genitals."
            ]
        
    },
    "kwambura": {
        "umuzi/root": "aambur",
        "basoma/phonetics": {
            " ": "kwaambura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwambura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gukura ku umuntu cg ku ikintu icyo cyari cyambaye","Déshabiller dévêtir enlever du corps ce qui sert de vêtement ou de garniture dans le sens défini .","To undress, to strip, to remove from the body what serves as clothing or adornment in the defined sense ."
            ]
        
        },
    "ubwambure ": {
        "umuzi/root": "aámbure",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwaámbure",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwambure",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuboneka nabi kw'ikintu cg ahantu hari hambaye iyo bahambuye","Vide déplaisant dû à la disparition d’un objet qu’on portait habituellement ou qui décorait un endroit.","Unpleasant emptiness caused by the disappearance of an object that one usually wore or that decorated a place."
            
            ]
    
    },
    "kwamburira": {
        "umuzi/root": "aamburir",
        "basoma/phonetics": {
            " ": "kwaamburira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamburira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Kwambura inka inyana ibyaye ukayiha indi", "Enlever à une vache son veau nouveau né pour le donner à une autre.","To take a newborn calf away from a cow to give it to another."
            ]
        
    },
    "icyamburo": {
        "umuzi/root": "aamburo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaamburo",
            "mu bwinshi/plural": "ibyaamburo"
        },
        "bandika/writing": "icyamburo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Uruhushya rwo kwambura umuntu ahabwa n'mutegetsi","Autorisation de détrousser reçue d’un supérieur.","Authorization to strip received from a superior."
            ]
        
    },
    "cyambwe": {
        "umuzi/root": "aambwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyaambwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyambwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikiyaga kiri mu burasirazuba bwa perefegitura ya Kibungo mu majyepfo ya Pariki y'akagra", "Lac situé dans la partie orientale de la préfecture de Kibungo à la limite méridionale du Parc national de l’Akagera.","Lake located in the eastern part of the Kibungo prefecture at the southern boundary of Akagera National Park."
            ]
    },
    "byambwenu": {
        "umuzi/root": "aambweénu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "byaambweénu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "byambwenu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inkuba irangira cyane bigatinda","Tonnerre qui retentit fort et longtemps","Thunder that resounds loudly and for a long time"
            ]
      
    },
    "rwamenyo": {
        "umuzi/root": "aameényo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaameényo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamenyo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu ufite amenyo manini kandi maremare asohoka cg ahingikiranye","Surnom donné à une pers qui a des dents grosses et longues saillantes ou superposées.","A nickname given to a person who has large, long, protruding, or overlapping teeth."
            ]
        
    },
    "umwami": {
        "umuzi/root": "aámi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaámi",
            "mu bwinshi/plural": "abaámi"
        },
        "bandika/writing": "umwami",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umutegetsi w'ikirenga w'igihugu ushyirwa ho asimbuuye ba se na ba sekuru","Roi monarque chef suprême d’un pays investi par la voie héréditaire.","King, monarch, supreme leader of a country invested through hereditary means."
            ]
            

    },
    "abami": {
        "umuzi/root": "aámi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaámi",
            "mu bwinshi/plural": "abaámi"
        },
        "bandika/writing": "abami",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugabe n'umugabekazi", "Le roi et la reine mère.","The king and the queen mother."
            ]
            
    },
    "inyami": {
        "umuzi/root": "amí",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inyamí",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inami",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ingoma" ,"Tambour dynastique","drum associated with a royal dynasty"
            ]
        
    },
    "ubwami": {
        "umuzi/root": "aámi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwaámi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwami",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubutegetsi bwa cyami","Royauté monarchie","Royalty monarchy"
             ]
        
    },
    "imbwami": {
        "umuzi/root": "aámi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbwaámi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbwami",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Mu rugo rw'umwami"," palais royal","royal palace"
            ]
         
    },
    "umwamikazi": {
        "umuzi/root": "aámikazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaámikazi",
            "mu bwinshi/plural": "abaámikazi"
        },
        "bandika/writing": "umwamikazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugore w'umwami","Reine épouse légitime du roi.","Reine épouse légitime du roi."
            ]
        
    },
    "amamikazi": {
        "umuzi/root": "aámikazi",
        "basoma/phonetics": {
            " ": "NA",
         "mu buke/singular": "amaámikaz",
         "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amamikazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "ubwoko bw'amateke afite ibibabi bisa n'ibitabaguye","Variété de colocase à feuilles composées","Variety of taro with compound leaves"
            ]
        
    },
    "kamikazi": {
        "umuzi/root": "aámikazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaámikazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamikazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'amasaka","Variété de sorgho","Variety of sorghum"
            ]
        
    },
    "rwamiko": {
        "umuzi/root": "aamikó",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamikó",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamiko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri perefegitura ya Gikongoro wahaye izina komini uri mo","Colline et commune de la préfecture de Gikongoro.","Hill and municipality of the Gikongoro prefecture."
            ]
            
        
    },
    "kwamira": {
        "umuzi/root": "áamir",
        "basoma/phonetics": {
            " ": "kwáamira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gukomera imbwa zihiga uzikaza","Exciter les chiens de chasse par des cris.","To excite the hunting dogs with cries."
            ]
        
    },
    "umwamira": {
        "umuzi/root": "áamirá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáamirá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwamira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'ikimera","Arbuste de la famille des Combrétacées","Shrub of the Combretaceae family"
            ]
        
    },
    "umwamirangabo": {
        "umuzi/root": "aamirangabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaamirangabo",
            "mu bwinshi/plural": "imyaamirangabo"
        },
        "bandika/writing": "umwamirangabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Agati ko mu turere tw'amashyamba yo mu misozi miremire no mu turere tw'ibisambu bitari mo ibiti byinshi gafite amashami avunika ubusa n'ibibabi binini byihariye n'uturabo tujya kuba umuhondo cg umutuku weruruka usa na divayi n'imbuto zumutse", "Arbuste ou petit arbre de la famille des Rubiacées Hymenodictyon floribundum.","Shrub or small tree of the Rubiaceae family, Hymenodictyon floribundum."
            ]
        
    },
    "kwamirira": {
        "umuzi/root": "áamirir",
        "basoma/phonetics": {
            " ": "kwáamirira",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamirira",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gukabukira inyamaswa cg umuntu ukamutesha ibyo yakoraga cg yavugaga","Empêcher arrêter faire taire par des cris.","To prevent, stop, silence by means of cries."
            ]
        
    },
    "akamiro": {
        "umuzi/root": "áamiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akáamiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akamiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Urusaku rwamira","Cris poussés pour empêcher d’agir.","Cries made to prevent action."
            ]
        
    },
    
    "umwamiya": {
        "umuzi/root": "aamiya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaamiya",
            "mu bwinshi/plural": "imyaamiya"
        },
        "bandika/writing": "umwamiya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'agati","Arbuste de la famille des Alangacées","Shrub of the Alangaceae family"
            ]
        
    },
    
    "urwamo": {
        "umuzi/root": "áamo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáamo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwamo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "urasaku","bruit","noise"
            ]
        
    },
    "rwampaka": {
        "umuzi/root": "aampaká",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaampaká",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwampaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ku gahato","De force.","By force"
            ]
        
    },
    "urwamu": {
        "umuzi/root": "áamu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwáamu",
            "mu bwinshi/plural": "inzáamu"
        },
        "bandika/writing": "urwamu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ijwi rirenga","Bruit cri aigu","Noisy, prolonged cry"
            ]
        
    },
    "rwamu": {
        "umuzi/root": "áamu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwáamu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ingoma y'ubwiru y'abatsobe","Tambour dynastique des ritualistes Tsobe","Dynastic drum of the Tsobe ritualists."
            ]
        
    },
    "rwamucurankumbi": {
        "umuzi/root": "aamúcurankúumbí",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamúcurankúumbí",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamucurankumbi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'icumu","Espèce de lance.","Type of spear."
            ]
        
    },
    "akamugani": {
        "umuzi/root": "aamúganí",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akaamúganí",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akamugani",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Gukora", "Commettre un acte répréhensible.","To commit a reprehensible act."
            ]
        
    },
    "ikamugani": {
        "umuzi/root": "áamuganí",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ikáamuganí",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ikamugani",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Mu gihugu cy'imigani.","Formule introductive des contes", "introductory formula of talesor opening formula of stories.",
                "Mbacire umugani mbabambuze umugani n'uzava ikamugani azasange ubukombe bw'umugani buziritse ku muganda w'inzu"
            ]
    },
    "kamugobeko": {
        "umuzi/root": "aamugóbeko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamugóbeko",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamugobeko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'umukino wo gusamata", "Jeu de jonglerie.","Juggling game"
            ]
        
    },
    "kamugote": {
        "umuzi/root": "aamugoóte",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamugoóte",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamugote",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umupira cg ikote bimara imbeho" ,"Vareuse"," jumper"
            ]
        
    },
    "kamugunguzi": {
        "umuzi/root": "aamuguunguúzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamuguunguúzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamugunguzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'umunyamahane", "Personne querelleuse.","Contentious person"
            ]
        
    },
    "rwamuhingamyi": {
        "umuzi/root": "aamúhiingamyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamúhiingamyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamuhingamyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'icumu","lance","type of a spear"
            ]
        
    },
    " rwamuhirima": {
        "umuzi/root": "aamúhiríma",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamúhiríma",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamuhirima",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Kugwa nzira waragiye gushaka amahaho","Mourir en allant chercher des vivres.","To die while going to fetch supplies"
            ]
        
    },
    "kamujwara": {
        "umuzi/root": "aamujwaára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamujwaára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamujwara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
            " Inzoga iva mu marwa y'uburo aturiye","Bière d’éleusine miellée","Mead of Eleusis."
            ]
        
    },
    "kwamuka": {
        "umuzi/root": "áamuuk",
        "basoma/phonetics": {
            " ": "kwáamuuka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamuka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuminuka kándi wihuta","Disparaître à toute allure.","To disappear at full speed."
            ]
        
    },
    "rwamukire": {
        "umuzi/root": "aamúkiré",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamúkiré",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamukire",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Intorezo y'ibwami bicishaga abantu","Hache d’exécution judiciaire à la cour royale.","Judicial execution axe at the royal court."
            ]
        
    },
    "kamukoti": {
        "umuzi/root": "aamukoóti",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamukoóti",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamukoti",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwambaro umeze nk'ikote ariko ukagira umukaba mu rukenyerero","Espèce de veste qui serre à la ceinture.","A kind of jacket that tightens at the waist."
            ]
        
    },
    "akamunani": {
        "umuzi/root": "aamúnaáni",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akaamúnaáni",
            "mu bwinshi/plural": "utwaamúnaáni"
        },
        "bandika/writing": "akamunani",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Gushaka Kwanduranya ku muntu","Chercher un prétexte de querelle de bataille chercher noise.","To look for a pretext for a quarrel or to seek trouble."
            ]
        
    },
    "icyamunara": {
        "umuzi/root": "áamunará",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáamunará",
            "mu bwinshi/plural": "ibyáamunará"
        },
        "bandika/writing": "icyamunara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igurishwa ry'ibintu rikorewe mu ruhame rw'abantu bagenda bapandisha igiciro ikintu kikaza gutwarwa n'uwarushije abandi kuvuga igiciro cyisumbuye","Vente publique aux enchères.","Public auction."
            ]
        
    },
    
    "icyamupfiro": {
        "umuzi/root": "áamupfíiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáamupfíiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyamupfiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amafaranga umuntu asuza uwo yariye mu rusimbi ariko ntibongere gukina","Somme d’argent qu’on donne gratuitement à l’adversaire qui a tout perdu à l’issue d’un jeu de hasard.","Sum of money given freely to the opponent who has lost everything at the end of a game of chance."
            ]
        
    },
    "kamurari": {
        "umuzi/root": "aamurári",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaamurári",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamurari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'urusenda","Variété de piment.","Variety of pepper."
            ]
        
    },
    "kwamuruka": {
        "umuzi/root": "áamuruk",
        "basoma/phonetics": {
            " ": "kwáamuruka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamuruka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kuzimira"," Disparaître","To disappear."
            ]
        
    },
    "kwamurura": {
        "umuzi/root": "áamurur",
        "basoma/phonetics": {
            " ": "kwáamurura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamurura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gukura umuntu cg ikintu ku cyo gihugiye ho kikigirira nabí","Chasser écarter en recourant ou non à la magie une personne ou un animal nuisible.","To chase away or remove a person or a harmful animal"
            ]
        
    },
    "urwamururo": {
        "umuzi/root": "áamururo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáamururo",
            "mu bwinshi/plural": "inzáamururo"
        },
        "bandika/writing": "urwamururo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ihembe bavuza rikica imvura", "Cor dont les conjurateurs de pluie se servent pour empêcher la pluie de tomber.","A horn that rain conjurers use to prevent rain from falling."
            ]
        
    },
    "rwamutwe": {
        "umuzi/root": "aamutwé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamutwé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamutwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Intwari igenda mu z'imbere", "Guerrier courageux qui marche en tête de la troupe","Brave warrior who leads the troop"
            ]
        
    },
    "kwamuza": {
        "umuzi/root": "áamuz",
        "basoma/phonetics": {
            " ": "kwáamuza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwamuza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "gutungurana","Survenir à l’improviste","To occur unexpectedly."
            ]
        
    },
    "cyamuzana": {
        "umuzi/root": "aamuzaána",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyaamuzaána",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyamuzana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Kubyina Kuba wijuse ntugire icyo wita ho", "Faire l’insouciant parce qu’on est repu","To act carefree because one is sated."
            ]
        
    },
    "ibyamvagara": {
        "umuzi/root": "aamvagara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyaamvagara",
            "mu bwinshi/plural": "ibyaamvagara"
        },
        "bandika/writing": "ibyamvagara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibisigazwa bidafite umumaro","Restes sans valeur déchets.","Worthless remains, waste."
            ]
        
    },
    "umwamvuri": {
        "umuzi/root": "áamvurí",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáamvurí",
            "mu bwinshi/plural": "imyáamvurí"
        },
        "bandika/writing": "umwamvurí",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umutaka","parapluie","umberella"
            ]
        
    },
    "rwamwa": {
        "umuzi/root": "aamwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaamwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwamwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu wamaganwa hose kubera ubugiranabi bwe cg imyifatire ye mibi","Pers chassée de partout pour son inconduite réprouvé paria.","A person driven away from everywhere for their disreputable conduct, a rejected pariah."
            ]
        
    },
    
    "bamwana": {
        "umuzi/root": "aamwáana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "baamwáana",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bamwana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita ababyeyi bahujwe n'isano ishingiye ku bushyingirane bw'abana babo","Le nom donné aux parents unis par le lien basé sur le mariage de leurs enfants.","The name given to parents united by the bond based on the marriage of their children."
            ]
        
    },
    "akamwanya": {
        "umuzi/root": "áamwaánya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akáamwaánya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akamwanya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
               "mukanya","dans l'instant","momentarily" 
            ]

    },
    "cyamwiha": {
        "umuzi/root": "áamwiiha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyáamwiiha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyamwiha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'ishaka", "Variété de sorgho.","variety of sorgham"
            ]
        
    },
    
    "kwana": {
        "umuzi/root": "aan",
        "basoma/phonetics": {
            " ": "kwaana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutaka ubitewe n'ububabare","Hurler de douleur.", "to scream in pain."
            ]
    },
    "kwana": {
        "umuzi/root": "aan",
        "basoma/phonetics": {
            " ": "kwaana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gutangira kuzana igitoki kw'insina","En parlant du bananier monter en fleur fleurir.","Speaking of the banana tree, to bloom."
            ]
    },
    "umwana": {
        "umuzi/root": "áana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáana",
            "mu bwinshi/plural": "abáana"
        },
        "bandika/writing": "umwana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
               " umuntu, inyamaswa cg ikimera kitarakura ngo gikomere", "Être vivant encore jeune p.","Still young living being."
            ]
        
    },
    "icyana": {
        "umuzi/root": "áana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyáana",
            "mu bwinshi/plural": "ibyáana"
        },
        "bandika/writing": "icyana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " umwana w'inyamaswa","Petit d’un animal.","Young of an animal or Offspring of an animal."
            ]
        
    },
    "kwana": {
        "umuzi/root": "áana",
        "basoma/phonetics": {
            " ": "kwáana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gusubira cg Gusaza ukajya uvuga ay'abana","Retomber en enfance ","to fall back into childhood as an elderly"
            ]
                  
    },
   
    
    "inyanabusa": {
        "umuzi/root": "ánabúsa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inyánabúsa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inyanabusa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Insina yana umwanana gusa","Bananier qui donne une fleur sans produire de régime.","Banana plant that produces a flower without yielding a bunch."
            ]
        
    },
    "ubwanacyambwe": {
        "umuzi/root": "áanacyaambwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwáanacyaambwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwanacyambwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akarere ku rwanda kari muri perefegitura ya Kigari kagizwe na za komini Butamwa Nyarugenge, Kanombe, Rubungo na Gikomero","Région du Rwanda située dans la préfecture de Kigali et incluant les communes de Butamwa ,Nyarugenge, Kanombe, Rubungo et Gikomero.","Region of Rwanda located in the Kigali prefecture, including the communes of Butamwa, Nyarugenge, Kanombe, Rubungo, and Gikomero."
            ]
        
    },
    "kwanaga": {
        "umuzi/root": "aanaag",
        "basoma/phonetics": {
            " ": "kwaanaaga",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwanaga",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kubika urwunge by'inkoko guhera mu museke","En parlant des coqs chanter à l’unisson à partir de l’aube.","Speaking of roosters crowing in unison from dawn."
            ]
        
    },
    "urwanaga": {
        "umuzi/root": "áanaagá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáanaagá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwanaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ukubika kw'inkoko zanaga", "Chant des coqs qui crient à l’unisson le matin.","Song of the roosters crowing in unison in the morning."
            ]
        
    },
    "kwanagura": {
        "umuzi/root": "aanagur",
        "basoma/phonetics": {
            " ": "kwaanagura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwanagura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kubyara abana benshi kandi vubavuba","Engendrer plusieurs enfants à la suite les uns des autres.","To bear several children one after the other."
            ]
        
    },
    "kwanama": {
        "umuzi/root": "áanam",
        "basoma/phonetics": {
            " ": "kwáanama",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwanama",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kuba ikintu kidatwikiriye cg kigaragara","Être à découvert être visible apparent.","To be exposed, to be visible, apparent."
            ]
        
        },
    "kanama": {
        "umuzi/root": "aanamá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaanamá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kanama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwezi kwa cumi n'abiri k'umwaka wa kinyarwaanda","Douzième lunaison de l’année traditionnelle rwandaise.","Twelfth lunar month of the traditional Rwandan year."
            ]
        
    },
    "inyanama": {
        "umuzi/root": "ánamá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inyánamá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inyanama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubayeho nabi"," Qui vit médiocrement","Who lives moderately."
            ]
        
    },
    "kwanamiza": {
        "umuzi/root": "áanamiz",
        "basoma/phonetics": {
            " ": "kwáanamiza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwanamiza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gutinyuka ugakora ikintu mu ruhame", "Oser faire qqch en public.","To dare to do something in public."
            ]
        
    },
    "urwanamo": {
        "umuzi/root": "áanamo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwáanamo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwanamo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ukuba ikintu kidatwikiriye kiri ahantu hagaragara","Le fait d’être à découvert.","The act of being exposed."
            ]
        
    },
    "kwanamuka": {
        "umuzi/root": "áanamuk",
        "basoma/phonetics": {
            " ": "kwáanamuka",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwanamuka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Kuva aho wari wanamye","Se retirer d’une position inconfortable.","To withdraw from an uncomfortable position."
            ]
        
    },
    "ubwanamukari": {
        "umuzi/root": "áanamúkari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwáanamúkari",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwanamukari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akarere ku rwanda kari mu majyepfo ya perefegitura ya Butare kiganje mo komini Ngoma, Nyaruhengeri, Ndora, Shyanda na Kigembe","Traditional region of Rwanda located in the southern part of the Butare prefecture, encompassing the communes of Ngoma, Nyaruhengeri, Ndora, Shyanda, and Kigembe."
            ]
        
    },
    "kwanamura": {
        "umuzi/root": "áanamur",
        "basoma/phonetics": {
            " ": "kwáanamura",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwanamura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Gukura ikintu aho cyari cyanamye","Retirer d’une position inconfortable.","To withdraw from an uncomfortable position."
            ]
        
    },
    "umwanana": {
        "umuzi/root": "áanaaná",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáanaaná",
            "mu bwinshi/plural": "imyáanaaná"
        },
        "bandika/writing": "umwanana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akantu kaba ku mutwe w'igitoki kakava mo uturabyo turi mo ubuki igihe cyose igitoki kitarakomera","Fleur du bananier."
            ]
        
    },
    "kanangazi": {
        "umuzi/root": "aanangázi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaanangázi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kanangazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inkingi itega uruhamo rw'umuryango","Pilier qui soutient l’auvent d’une maison traditionnelle.","Column that supports the awning of a traditional house."
    
            ]
        
    },
    "kwananirwa": {
        "umuzi/root": "áanaanirw",
        "basoma/phonetics": {
            " ": "kwáanaanirwa",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwananirwa",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kubura uko ugira","Ne pas savoir quoi faire être dans l’embarras.","Not knowing what to do, being in a predicament."
            ]
        
        },
    "akananwa": {
        "umuzi/root": "áanaanwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akáanaanwá",
            "mu bwinshi/plural": "utwáanaanwá"
        },
        "bandika/writing": "akananwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Igice cy'umubiri kiri munsi y'umunwa akenshi kimera ho ubwanwa", "Menton.","Chin."
            ]
        
    
    },
    "akanapfu": {
        "umuzi/root": "áanapfu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akáanapfu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akanapfu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ishyano umuntu aba agushije iyo apfushije umwana","Événement shyano marqué par la perte d’un enfant.","Shyano event marked by the loss of a child."
            ]
        
    },
    "kwanda": {
        "umuzi/root": "aand",
        "basoma/phonetics": {
            " ": "kwaanda",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwanda",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kurambika ibintu ahantu utabitandukanya bigafata umwanya mugari","Répandre sur une grande surface.","To Spread over a large area."
            ]
        
    },
    "kwandura": {
        "umuzi/root": "aandur",
        "basoma/phonetics": {
            " ": "kwaanduru",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandura",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gufata umwanda by'umuntu cg ikintu", "Devenir sale se salir.","To become dirty, to get dirty."
            ]
        
    },
    
    "umwanda": {
        "umuzi/root": "aanda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwaanda",
            "mu bwinshi/plural": "imyaanda"
        },
        "bandika/writing": "umwanda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ububi buterwa no gucafura cg isuku nke by'umuntu cg ikintu","Saleté malpropreté.","Dirtiness, uncleanliness."
            ]
    },
    "itaburiya": {
        "umuzi/root": "taburiya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "itaburiya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "itaburiya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umwenda wikinga ku yindi myenda","tablier","apron"
            
        ]
    },
    "urwanda": {
        "umuzi/root": "aanda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaanda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwanda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "IgihUgu cyo muri Afurika yo hagati gikikijwe n'ubuganda, Kongo, Uburundi na Tanzaniya","pay africain","country in central east africa"
            ]
        
    },
    "akanda": {
        "umuzi/root": "aánda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akaánda",
            "mu bwinshi/plural": "utwaánda"
        },
        "bandika/writing": "akanda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "igihe cy'ibura ry'ibitunga abantu","Légère pénurie de vivres disette qui s’étend progressivement","Light food shortage, famine that is gradually spreading."
            ]
        
    },
    "kwandabagana": {
        "umuzi/root": "aandabagan",
        "basoma/phonetics": {
            " ": "kwaandabagana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandabagana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
        
                "kwiyenza","Chercher noise","To seek trouble"
            ]
            

        
    },
    "kwandabana": {
        "umuzi/root": "aandaban",
        "basoma/phonetics": {
            " ": "kwaandabana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandabana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kwivanga mu bitakureba bigatera umuntu imbogamizi","Se mêler des affaires d’autrui en le gênant.","To meddle in others' affairs while bothering them."
            ]
        
    },
    "kwandabirana": {
        "umuzi/root": "aandabiran",
        "basoma/phonetics": {
            " ": "kwaandabirana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandabirana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kwiyenza", "Chercher noise","To seek trouble"
            ]
        
        
    },
    "amandabirane": {
        "umuzi/root": "aándabirane",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amaándabirane",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amandabirane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amahane ashingiye ku mwanduranyo","Querelle sans fondement.","Groundless dispute or Baseless quarrel."
            ]
        
    },
    "urwandabirane": {
        "umuzi/root": "aándabirane",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwaándabirane",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwandabirane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amagambo atarukira umuntu akurizaho umwanduranyo","Paroles provocantes de qui cherche noise.","Provocative words from someone looking for trouble."
            ]
        
    },
    "kwandagara": {
        "umuzi/root": "aandagar",
        "basoma/phonetics": {
            " ": "kwaandagara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandagara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Kunyanyagira kw'ibintu cg kuba aho bitagombaga kuba kubera umwete muke w'ubishinzwe","En parlant d’objets traîner négligemment un peu partout.","Speaking of objects lying around carelessly everywhere."
            ]
    
    },
    "umwandagara": {
        "umuzi/root": "áandagára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwáandagára",
            "mu bwinshi/plural": "imyáandagára"
        },
        "bandika/writing": "umwandagara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ikimera","Espèce de plante non identifiée.","Species of unidentified plant."
            ]
        
    },
    "kwandagatana": {
        "umuzi/root": "aandagatan",
        "basoma/phonetics": {
            " ": "kwaandagatana",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandagatana",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kwiyenza","Chercher noise","To seek trouble"
            ]
        
    },
    "kwandagaza": {
        "umuzi/root": "aandagaz",
        "basoma/phonetics": {
            " ": "kwaandagaza",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandagaza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Gukwiza inkuru isebanya","Diffuser une médisance.","To spread a rumor or To disseminate a slander"
            ]

    },
    "inyandagazi": {
        "umuzi/root": "andagazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inandagazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inandagazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
    
                "umuntu ugayitse ariko udateje ikibazo ku bandi","Pers vile mais inoffensive","Vile but harmless person."
            ]
        
    },
    "kwandama": {
        "umuzi/root": "aandam",
        "basoma/phonetics": {
            " ": "kwaandama",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandama",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kwitegura gukora ikintu runaka","Se mettre à faire","To start doing "
            ]
    
        
    },
    "cyandani": {
        "umuzi/root": "aandaáni",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyaandaáni",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyandani",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'ikijumba","Espèce de patate douce.","Type of sweet potato."
            ]
        
    },
    "kwandara": {
        "umuzi/root": "aandaar",
        "basoma/phonetics": {
            " ": "kwaandaara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandara",
        "icyiciro/pos": [
            "verb",
            "insinga"
        ],
        "igisobanuro/meaning": [
            
                " Kugenda buhoro cyane kubera intege nke cg uburwayi","Marcher péniblement se traîner par l’effet de la faiblesse ou d’une maladie.","To walk laboriously, dragging oneself due to weakness or illness."
            ]
        
    },
    
    "kwandara": {
        "umuzi/root": "aandaar",
        "basoma/phonetics": {
            " ": "kwaandaara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                " Kuzengurutsa ahantu umuriro by'abahigi bashaka kuvumbura inyamaswa", "Allumer un feu autour d’un terrain pour lever le gibier.","To light a fire around a field to drive up game."
            ]
        
    },
    "rwandara": {
        "umuzi/root": "aandaará",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwaandaará",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwandara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Izina bita umuntu ugenda yandara cg akururuka","Surnom d’une pers qui marche en se traînant lentement.","Nickname for a person who walks slowly, dragging themselves."
            ]

    },
    "amandaranda": {
        "umuzi/root": "aandaraanda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amaandaraanda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amandaranda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
    
                "Amagambo y'urudaca kandi atanogeye amatwi","Bavardage interminable et déplaisant.","Endless and unpleasant chatter."
            ]
        
    },
    "kwandarara": {
        "umuzi/root": "aandarar",
        "basoma/phonetics": {
            " ": "kwaandarara",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandarara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
        
                "kubura agaciro kw'ikintu kiri hose ku karubanda"," Traîner","To drag"
            
            ]

    },
    "akandare": {
        "umuzi/root": "aándaare",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akaándaare",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akandare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ingeso cg indwara y'akarande mu nzu iyi n'iyi",  "Vice ou maladie héréditaire.","Vice or hereditary disease."
            
            ]
    },
    "kwandarika": {
        "umuzi/root": "aandarik",
        "basoma/phonetics": {
            " ": "kwaandarika",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwandarika",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
        
                "Kureka ibintu cg umuntu akandarara","Laisser traîner en désordre ne pas prendre soin de.","To leave in disorder, not to take care of."
                
        ]
    },
    "icyandaro": {
        "umuzi/root": "áandaaro",
        "basoma/phonetics": {
            " ": "NA",
           "mu buke/singular": "icyáandaaro",
             "mu bwinshi/plural": "ibyáandaaro"
        },
        "bandika/writing": "icyandaro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Umuriro uzengurutse igisambu","Feu allumé autour d’un terrain par des chasseurs.","Fire lit around a field by hunters."
            ]
        
    },
        "kwandavura": {
            "umuzi/root": "aandavur",
            "basoma/phonetics": {
                " ": "kwaandavura",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandavura",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kwandura cyane","Devenir très sale.","To become very dirty."
                ]
            
  },
   
        "kwandaza":{
            "umuzi/root": "aandaaz",
            "basoma/phonetics": {
                " ": "kwaandaaza",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandaza",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "iyo ibice by'imbere mu nda bisohotse hanze","Avoir un prolapsus","To have a prolapse"
                ]
            
        },
        "icyandi": {
            "umuzi/root": "aandi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyaandi",
                "mu bwinshi/plural": "ibyaandi"
            },
            "bandika/writing": "icyandi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Ubwoko bw'inyoni ikunda kwarika ku bibabi by'amasaka","Espèce de petit oiseau qui niche souvent sur les feuilles de sorgho.","Species of small bird that often nests on sorghum leaves."
                ]
            
        },
        "kwandika": {
            "umuzi/root": "aandik",
            "basoma/phonetics": {
                " ": "kwaandika",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandika",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    " Gutora inkwi ukagenda urunda udukaba","Ramasser du bois de chauffage en faisant de petits tas (pour libérer les bras à mesure qu’on avance).","Collect firewood by making small piles"
                ]
            
        },
        "kwandika": {
            "umuzi/root": "aandik",
            "basoma/phonetics": {
                " ": "kwaandika",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandika",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    " Gushushanya inyuguti zigize amagambo ubigirishije igikoresho kibonetse cyose nk'ikaramu imashini bakubita ho intoki nibindi",  "Écrire","to write"
                ]
            
        },
        
        "ubwandike": {
            "umuzi/root": "aándike",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ubwaándike",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubwandike",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                "ibyanditswe","Texte écrit","Written text."
               
            ]
            
        },
        "imyandiko": {
            "umuzi/root": "aandiko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaandiko",
                "mu bwinshi/plural": "Imyaandiko"
            },
            "bandika/writing": "Imyandiko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Kamwe mu dukaba twinshi umuntu agenda asiga hirya no hino aho yagiye anyura atashya inkwi zo gucana","Petit tas de bois de chauffage qu’on laisse par terre pendant qu’on continue le ramassage.","Small pile of firewood left on the ground while continuing to gather."
                ]
                
        },
        "imyandiko": {
            "umuzi/root": "aandiko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaandiko",
                "mu bwinshi/plural": "Imyaandiko"
            },
            "bandika/writing": "Imyandiko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu cyanditse gisobanura ku buryo burambuye","Texte écrit rédigé un écrit.","Written text, a written document."
            
                ]
        },
        "urwandiko": {
            "umuzi/root": "aandiko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwaandiko",
                "mu bwinshi/plural": "inzaandiko"
            },
            "bandika/writing": "urwandiko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " ibaruwa","Lettre","letter"
                ]
            
        },
        "kwandira": {
            "umuzi/root": "aandir",
            "basoma/phonetics": {
                " ": "kwaandira",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandira",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "guhumbahumba urwiri", "Ramasser le chiendent dans un guéret.","To gather couch grass in a clearing"
                ]
                
        },
        "umwando": {
            "umuzi/root": "aando",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaando",
                "mu bwinshi/plural": "imyaando"
            },
            "bandika/writing": "umwando",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                " Akambaro gato k'impuzu cg k'uruhu kambarwaga n'abana","Petit vêtement d’écorce ou de peau que les enfants portaient autrefois (autour de la taille).","Small garment made of bark or skin that children used to wear (around the waist)."
                ]
        },
        "umwandu": {
            "umuzi/root": "aándu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaándu",
                "mu bwinshi/plural": "abaándu"
            },
            "bandika/writing": "umwandu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Umuzimu w'umugabo wapfuye atarongoye utera umukobwa bamumurikiye","Esprit de ceui qui est mort sans s’être marié qui s’en prend à une fille qu’on lui a symboliquement promise en mariage.","The spirit of one who died unmarried, who takes vengeance on a girl who was symbolically promised to him in marriage."
                
             ]
        },
        "imyandu": {
            "umuzi/root": "aándu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaándu",
                "mu bwinshi/plural": "imyaándu"
            },
            "bandika/writing": "Imyandu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ibintu umuntu upfuye asiga","Biens laissés par un défunt","Property left by a deceased person"
            ]
        },
        "amandu": {
            "umuzi/root": "aándu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "amaándu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "amandu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "indwara y'uruhu yandura","Maladie de la peau attrapée par contagion","contagious skin disease."
                ]
        },
        "ubwandu": {
            "umuzi/root": "aándu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ubwaándu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubwandu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " ikintu cyakuye ku kindi", "Saleté dont on est souillé par contact.","Filth that one is soiled with by contact."
                 ]
        },
        "imyandu": {
            "umuzi/root": "aándu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaándu",
                "mu bwinshi/plural": "Imyaándu"
            },
            "bandika/writing": "Imyandu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " ubwoko bw'ibara", "Espèce de tache sur les viscères d’un poussin divinatoire.","A type of stain on the entrails of a divinatory chick."
                
                ]
        },
        "kwandukira": {
            "umuzi/root": "aandukiir",
            "basoma/phonetics": {
                " ": "kwaandukiira",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandukira",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                     " Kwanduza cyane by'indwara", "En parlant d’une maladie être très contagieuse.","When talking about a disease, to be very contagious."
                 ]
        },
        "kwandukura": {
            "umuzi/root": "aandukuur",
            "basoma/phonetics": {
                " ": "kwaandukuura",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandukura",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    " Gusubira mu ibintu byanditse ukabyandika ahandi","Copier transcrire.",
                ]
        },
        "kwandura": {
            "umuzi/root": "aandur",
            "basoma/phonetics": {
                " ": "kwaandura",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandura",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gufatwa n'indwara ikomotse ku wundi muntu","Être contaminé par autrui.","To be contaminated by others."
                ]
        },
        "kwandura": {
            "umuzi/root": "aanduur",
            "basoma/phonetics": {
                " ": "kwaanduura",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandura",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gukura inkwi aho ziri zanitse","Ramasser les petits tas de bois de chauffage.","To collect the small piles of firewood."
                ]
        },
        "ingeso": {
            "umuzi/root": "geso",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ingeso",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ingeso",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "akamenyero k'ikibi","mauvaise habitude","bad habit"
                ]
            
        },
        "kwanduranya": {
            "umuzi/root": "aandurany",
            "basoma/phonetics": {
                " ": "kwaanduranya",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwanduranya",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    " Gushaka impamvu y'amahane ku muntu","provoquer.","To provoke someone."
                
                 ]
            
        },
        "umwanduranyo": {
            "umuzi/root": "aanduranyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaanduranyo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umwanduranyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukwitoratoza ku muntu umushaka ho amahane","provocation.","provocation"
                ]
        },
        "ubwandure": {
            "umuzi/root": "aándure",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ubwaándure",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubwandure",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukuba ikintu gifite umwanda","Saleté.","Mess or dirt."
                ]
        },
        "ubwandure": {
            "umuzi/root": "aándure",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ubwaándure",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubwandure",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                    " Indwara umuntu yanduye","Maladie attrapée par contagion","communicable disease"
                ]
        },
        "kwanduruka": {
            "umuzi/root": "aanduruk",
            "basoma/phonetics": {
                " ": "kwaanduruka",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwanduruka",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "kuva ahantu werekeza ahandi"," Quitter","To leave"
                ]
        },
        "kwandurura": {
            "umuzi/root": "aandurur",
            "basoma/phonetics": {
                " ": "kwaandurura",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwandurura",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "kwirukana","Mener paître","To lead to graze."
                ]
        },
        "kwanduza": {
            "umuzi/root": "aanduz",
            "basoma/phonetics": {
                " ": "kwaanduza",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwanduza",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "gutuma ikintu gisa nabi","Salir","make something dirty"
                ]
        },
        "kwanga": {
            "umuzi/root": "áang",
            "basoma/phonetics": {
                " ": "kwáanga",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwanga",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gukura umuntu cg ikintu ho umutima","détester.","to detest"
                ]
       
        },
        "amanga": {
            "umuzi/root": "áanga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "amáanga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "amanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": 
                [
                    "kutagira ubwoba cg amasonisoni"," être audacieux","audacity"
                ]
        },
        
        "umwanga": {
            "umuzi/root": "aánga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaánga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umwanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Agahinda cg ukwijima bigaragara mu maso","Mélancolie ou humeur qui se marque sur le visage.","Melancholy or mood that is reflected on the face."
                 ]
        },
        "icyanga": {
            "umuzi/root": "aánga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "Icyaánga",
                "mu bwinshi/plural": "Ibyaánga"
            },
            "bandika/writing": "Icyanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwobo w'igisoro uri mo ubusa","Godet vide au jeu de godets.","Empty cup in the cup game",
                    "imiryohere y'ikintu"
                ]
        },
        "urwanga": {
            "umuzi/root": "aánga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwaánga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "urwanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igikoma cyeruruka kubera ko kidahiye","Bouillie trop peu cuite","Under-cooked porridge"
                ]
        },
        "akanga": {
            "umuzi/root": "aánga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akaánga",
                "mu bwinshi/plural": "utwaánga"
            },
            "bandika/writing": "akanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'akatsi kageza kuri santimetero kamara imyaka igera kuri ibiri karyama ku butaka rimwe na rimwe kagashinga amashami","Herbe pérenne de la famille des Caesalpiniaceae ","Perennial herb of the Caesalpiniaceae family"
                ]
        },
        "kwangabara": {
            "umuzi/root": "áangabar",
            "basoma/phonetics": {
                " ": "kwáangabara",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangabara",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "kwenda kurangiza", "Être sur le point de finir","To be about to finish."
                ]
        },
        "inyangabirama": {
            "umuzi/root": "áangabírama",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangabírama",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangabirama",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                    "umuntu ugambirira guteza abandi amage","qui agit au détriment de","who acts to the detriment of"
                ]
        },
        "inyangabugwate": {
            "umuzi/root": "áangabúgwaáte",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangabúgwaáte",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangabugwate",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umuntu ugaragaza ubuto kurusha imyaka ye","Personne petite et mince paraissant moins que son âge","Small and slim person appearing younger than their age."
                ]
        },
        "inyangabukwerere": {
            "umuzi/root": "áangabúkweérere",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangabúkweérere",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangabukwerere",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu mugufi unanutse kandi utapfa kumenya ko akuze", "Personne petite et mince paraissant moins que son âge.","Small and slim person appearing younger than their age."
                 ]
        },
        "umwangacucu": {
            "umuzi/root": "áangacuucu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwáangacuucu",
                "mu bwinshi/plural": "abáangacuucu"
            },
            "bandika/writing": "umwangacucu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'isaro ritukura", "Espèce de perle rougeâtre.","Type of reddish pearl."
                ]
        },
        "umwangahavu": {
            "umuzi/root": "áangahávu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwáangahávu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umwangahavu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ibihe by'imbeho","Temps froid","Cold weather."
                ]
        },
        "icyangahereri": {
            "umuzi/root": "áangahéreri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáangahéreri",
                "mu bwinshi/plural": "ibyáangahéreri"
            },
            "bandika/writing": "icyangahereri",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'ikimera","Espèce de plante non identifiée.","Species of unidentified plant."
                ]
        },
        "inyangakubwirwa": {
            "umuzi/root": "áangakúbwiirwa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangakúbwiirwa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangakubwirwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umuntu utumva inama z'abandi","Qui refuse les conseils","Who refuses advice."
                ]
        },
        "umwangakurutwa": {
            "umuzi/root": "áangakurutwa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwáangakurutwa",
                "mu bwinshi/plural": "abáangakurutwa"
            },
            "bandika/writing": "umwangakurutwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
    
                    "Umuntu mwiza ku mubiri bitagira urugero", "Personne d’une beauté incomparable","Person of unmatched beauty"
                ]
        },
        "inyangamatare": {
            "umuzi/root": "áangamátare",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangamátare",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangamatare",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'inyoni","Caille commune","Common quail"
                ]
        },
        "urwangamazimwe": {
            "umuzi/root": "áangamázimwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwáangamázimwe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "urwangamazimwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ahantu umuntu yigira cg atura hitaruye aho abandi bari cg batuye","lieu où l’on va pour vivre retiré ou être loin des gens","to live in seclusion or be away from people"
                ]
        },
        "icyangaminwe": {
            "umuzi/root": "aangaminwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyaangaminwe",
                "mu bwinshi/plural": "ibyaangaminwe"
            },
            "bandika/writing": "icyangaminwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umwana w'umushishe ucyigaragura ku ngobyi", "Gros bébé qui s’agite encore sur le dos.","Big baby still wriggling on its back."
                ]
        },
        "icyangamubyizi": {
            "umuzi/root": "aangamubyizi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyaangamubyizi",
                "mu bwinshi/plural": "ibyaangamubyizi"
            },
            "bandika/writing": "icyangamubyizi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umunebwe"," Paresseux","Sloth"
                ]
        },
        "icyangamuce": {
            "umuzi/root": "áangamúce",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáangamúce",
                "mu bwinshi/plural": "ibyáangamúce"
            },
            "bandika/writing": "icyangamuce",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umwana uri mu kigero utasanga aho wamusize","Enfant en bas âge","Young child or Toddler."
                ]
        },
        "icyangamuganda": {
            "umuzi/root": "áangamugaanda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáangamugaanda",
                "mu bwinshi/plural": "ibyáangamugaanda"
            },
            "bandika/writing": "icyangamuganda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "uruti runini rw'inganzamarumbo"," Tronc d’arbre","Tree trunk."
                ]
        },
        "inyangamugayo": {
            "umuzi/root": "aangamugayo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyaangamugayo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangamugayo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umuntu w'imico ntangarugero","Homme honnête","Honest man"
                ]
        },
        "akangamurizo": {
            "umuzi/root": "áangamuriizo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akáangamuriizo",
                "mu bwinshi/plural": "utwáangamuriizo"
            },
            "bandika/writing": "akangamurizo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Akagufa k'urutirigongo gasuma hagati y'ibibuno","Coccyx","Coccyx"
                ]
        },
        "inyangamutongano": {
            "umuzi/root": "áangamútoongano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangamútoongano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangamutongano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                   "umuntu udakunda amahane" ,"qui refuse a disputer","someone who avoids disputes"
                ]
        },
        "kwangana": {
            "umuzi/root": "áangan",
            "basoma/phonetics": {
                " ": "kwáangana",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangana",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    " Kugira umutima wanga abandi", "Être haineux","To be hateful"
                ]
        },
        "inyangane": {
            "umuzi/root": "ángané",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyángané",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangane",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "urwango","Haine","Hate"
                ]
        },
        
        "icyanganga": {
            "umuzi/root": "áangaangá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "Icyáangaangá",
                "mu bwinshi/plural": "Ibyáangaangá"
            },
            "bandika/writing": "Icyanganga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Umutako abagore bambara mu ruhanga ugizwe n'umugozi utunze ho isaro rimwe cg abiri","Parure de femme portée au front et consistant en une ou deux perles enfilées sur une corde.","A woman's adornment worn on the forehead, consisting of one or two pearls strung on a cord."
                ]
        },
        "umwangange": {
            "umuzi/root": "áangaangé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwáangaangé",
                "mu bwinshi/plural": "imyáangaangé"
            },
            "bandika/writing": "umwangange",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ikimera","Espèce de plante non identifiée","Unidentified plant species"
                ]
        },
        "kwangangiza": {
            "umuzi/root": "áangaangiz",
            "basoma/phonetics": {
                " ": "kwáangaangiza",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangangiza",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "gukorangiza imfizi cg umuntu kugira ngo birwane", "Inciter un taureau ou une pers à se battre.","To incite a bull or a person to fight."
                 ]
        },
        "icyangangwe": {
            "umuzi/root": "áangaangwé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáangaangwé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "icyangangwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "kubihirwa"," Dégoût","Disgust."
                ]
        },
        "ibyanganjagasha": {
            "umuzi/root": "áanganjágasha",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáanganjágasha",
                "mu bwinshi/plural": "ibyáanganjágasha"
            },
            "bandika/writing": "ibyanganjagasha",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ibishyimbo bahinga ku ibabi ry'amasaka mbere y'injagasha","Haricots plantés peu avant la saison des jagásha .","Beans planted just before the jagásha season."
                ]
        },
        "urwangano": {
            "umuzi/root": "áangano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwáangano",
                "mu bwinshi/plural": "inzáangano"
            },
            "bandika/writing": "urwangano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Urwango ruri hagati y'abantu babiri cg benshi","Haine réciproque.","Mutual hatred"
                ]
        },
        "akanganteba": {
            "umuzi/root": "áanganteba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akáanganteba",
                "mu bwinshi/plural": "utwáanganteba"
            },
            "bandika/writing": "akanganteba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Umwobo wa gatatu cg wa gatandatu w 'igisoro ku murongo w'imbere uturutse iburyo ugana i bumoso bw'umwe mu bakinnyi","Troisième ou sixième godet de la rangée interne du jeu de godets en allant de droite à gauche dans le camp du joueur.","Third or sixth cup of the inner row of the cup game, moving from right to left in the player's camp."
                 ]
        },
        "akanganteba": {
            "umuzi/root": "áanganteba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akáanganteba",
                "mu bwinshi/plural": "utwáanganteba"
            },
            "bandika/writing": "akanganteba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Akabindi gaciye munsi y'inteba","Pot en terre cuite dont la capacité est inférieure à celle du pot teba .","Clay pot with a capacity smaller than that of the teba pot"
                ]
        },
        "kwanganya": {
            "umuzi/root": "áangany",
            "basoma/phonetics": {
                " ": "kwáanganya",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwanganya",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "kubagarira cg gukingurura","Eclaircir une plantation","To thin out a plantation."
                ]
        },
        "umwanganyo": {
            "umuzi/root": "áanganyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwáanganyo",
                "mu bwinshi/plural": "imyáanganyo"
            },
            "bandika/writing": "umwanganyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ibihingwa byabagariwe","Plantation éclaircie","thinned out plantation"
                ]
            },         
        "kwangara": {
            "umuzi/root": "aangaar",
            "basoma/phonetics": {
                " ": "kwaangaara",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangara",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "kwerera cg kubungera","Vagabonder errer","To wander aimlessly"
                ]
        },
        "akangaratete": {
            "umuzi/root": "aangarateete",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akaangarateete",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "akangaratete",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Gusiga cg guta cg Gutererana uri mu kaga cg mu byago","Abandonner qqn dans le malheur","abandon someone in misfortune"
                ]
        },
        "umwangare": {
            "umuzi/root": "aángaare",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaángaare",
                "mu bwinshi/plural": "imyaángaare"
            },
            "bandika/writing": "umwangare",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ikimera", "Espèce de plante non identifiée.","Species of unidentified plant."
                ]
        },
        "akangari": {
            "umuzi/root": "aangari",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akaangari",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "akangari",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu ubangamye","gêneur, pers insupportable","Annoying person"
                ]
        },
        "akangari": {
            "umuzi/root": "aangari",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akaangari",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "akangari",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwinshi","Nombreux","Numerous."
    
                ]
        },
        "kwangarika": {
            "umuzi/root": "aangarik",
            "basoma/phonetics": {
                " ": "kwaangarika",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangarika",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gusiga umuntu mu kaga cg mu byago","Laisser qqn dans l’embarras ou dans la misère.","To leave someone in misery."
                ]
        },
        "icyangaro": {
            "umuzi/root": "aangaaro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyaangaaro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "icyangaro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukugenda nta cyo ugamije", "Errance vagabondage.","Wandering"
                ]
        },
        "akangaru": {
            "umuzi/root": "áangarú",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akáangarú",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "akangaru",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ibintu guhindura isura bitunguranye","malheur inattendu","unanticipated misfortune"
                ]
        },
        "icyangarubingo": {
            "umuzi/root": "áangarubiingo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáangarubiingo",
                "mu bwinshi/plural": "ibyáangarubiingo"
            },
            "bandika/writing": "icyangarubingo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Ubwoko bw'ikimera","Espèce de plante non identifiée","Species of unidentified plant"
                 ]
        },
        "icyangaruhimbi": {
            "umuzi/root": "áangaruhiimbi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáangaruhiimbi",
                "mu bwinshi/plural": "ibyáangaruhiimbi"
            },
            "bandika/writing": "icyangaruhimbi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                   "udashaka gukora","Femme sotte","who detests working"
                ]
        },
        "inyangarupfuko": {
            "umuzi/root": "áangarúpfuko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangarúpfuko",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangarupfuko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igisebe kinini cyagaze kigahora kininda amashyira","Plaie purulente qui s’élargit constamment","Purulent wound"
                ]
        },
        "inyangarwanda": {
            "umuzi/root": "aangarwaanda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyaangarwaanda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyangarwanda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umunyamanyanga"," Personne malhonnête","Dishonest person"
                ]
        },
        "ubwangati": {
            "umuzi/root": "áangati",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ubwáangati",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubwangati",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Umwuka mubi uturuka mu gifu umuntu akawutura nk'umubi","Renvoi d’estomac éructation flatulence malodorante.","Stomach reflux"
                ]
        },
        "umwangato": {
            "umuzi/root": "aangato",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaangato",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umwangato",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igiti kiri hagati yo kuba umuganda no kuba inkingi","Tronc d’arbre qui sert dans la construction de la maison traditionnelle","Tree trunk used in the construction of traditional houses"
                ]
        },
        "umwangato": {
            "umuzi/root": "aangato",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaangato",
                "mu bwinshi/plural": "imyaangato"
            },
            "bandika/writing": "umwangato",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inyundo nto abacuzi bifashisha bacura ibyuma bito cg bahozoza ibinini","Petit marteau dont les forgerons se servent pour travailler les petits objets","Small hammer used by blacksmiths for working on small objects"
                 ]
        },
        "umwangato": {
            "umuzi/root": "aangato",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaangato",
                "mu bwinshi/plural": "imyaangato"
            },
            "bandika/writing": "umwangato",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ikimera", "Espèce de plante non identifiée.","Species of unidentified plant."
                ]
        },
        "kwangatwa": {
            "umuzi/root": "aangatw",
            "basoma/phonetics": {
                " ": "kwaangatwa",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangatwa",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "kuba wariye wananyoye cyane","avoir assez de ce qu’on a mangé ou bu","To be full from what one has eaten or drunk."
                ]
        },
        "umwangavu": {
            "umuzi/root": "áangavú",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwáangavú",
                "mu bwinshi/plural": "abáangavú"
            },
            "bandika/writing": "umwangavu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umukobwa umaze kumera amabere","Jeune fille pubère","a girl whose breasts are developing"
                ]
      
        },
        "amangazini": {
            "umuzi/root": "áangaziíni",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "amáangaziíni",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "amangazini",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                   "aho bahahira", "magasin","grocery store"
                ]
        },
        "umwange": {
            "umuzi/root": "aánge",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwaánge",
                "mu bwinshi/plural": "imyaánge"
            },
            "bandika/writing": "umwange",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ikimera bagaburira inkwavu","Espèce de plante non identifiée","Species of unidentified plant"
                ]
        },
        "inyange": {
            "umuzi/root": "áangé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyáangé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyange",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "NONE","Haine","Hate."
                ]
        },
        "urwange": {
            "umuzi/root": "áangé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwáangé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "urwange",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko  bw'inyoni ziba mu nka","Espèce d'oiseaux","bird species"
                 ]
        },
        "kwangira": {
            "umuzi/root": "áangir",
            "basoma/phonetics": {
                " ": "kwáangira",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangira",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    " Kubera undi indashoboka","refuser","To be hard or unyielding"
                ]
        },
        "kwangirika": {
            "umuzi/root": "áangiirik",
            "basoma/phonetics": {
                " ": "kwáangiirika",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangirika",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kumera nabi kw'ibintu byari bimeze neza","s’abîmer.","to become damaged."
                ]
        },
        "kwangirira": {
            "umuzi/root": "áangirir",
            "basoma/phonetics": {
                " ": "kwáangirira",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangirira",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gukora ikintu utabyitaye ho","Faire négligemment à contrecoeur.","To do something carelessly and reluctantly"
                ]
        },
        "icyangiro": {
            "umuzi/root": "áangiro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyáangiro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "icyangiro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ikintu umuntu muri kamere cg mu miterere ye gituma abandi bamwanga", "Répulsion répugnance dédain que l’on inspire.","disdain that one inspires"
                ]
        },
        "igikundiro": {
            "umuzi/root": "kúundiro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "igikúundiro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "igikundiro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ikintu mu miterere cg imyitwarire gituma umuntu akundwa","personne charismatique","charismatic person"
                ]
        },
        "akangiryi": {
            "umuzi/root": "aangiryi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akaangiryi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "akangiryi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ishyari"," Jalousie","Jealousy."
                ]
        },
        "kwangishira": {
            "umuzi/root": "aangishir",
            "basoma/phonetics": {
                " ": "kwaangishira",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangishira",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kugira amata kw'inka kurusha uko byari bisanzwe","En parlant d’une vache donner plus de lait que d’ordinaire.","to give more milk than usual."
                ]
        },
        "kwangiza": {
            "umuzi/root": "áangiiz",
            "basoma/phonetics": {
                " ": "kwáangiiza",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kwangiza",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kwica cg konona ikintu kigahinduka uko kitagombaga kumera cg kucyica kitaratungana cg guhindanya ikintu","Abîmer","To damage"
              ]
        },
        
        
        "umuryango": {
            "umuzi/root": "aango",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umuryaango",
                "mu bwinshi/plural": "imiryaango"
            },
            "bandika/writing": "umwango",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "urugi"," Porte","Door."
                ]
        },
        "inyango": {
            "umuzi/root": "aango",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyaango",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyango",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'ikimera"," Espèce de plante","Species of plant."
                ]
        },
        "urwango": {
            "umuzi/root": "áango",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwáango",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "urwango",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umutima umuntu agira wo kudakunda undi","Haine","Hate"
                ]
        },
        "ryangombe": {
            "umuzi/root": "áangoombe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ryáangoombe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ryangombe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina ry'umuntu bakeka ko ari we wahimbye ibyo kubandwa","Héros légendaire fondateur du culte rendu aux esprits maándwa .","Legendary hero and founder of the worship of the maándwa spirits."
                ]
        },
        "imbabagurwa": {
        "umuzi/root": "babágurwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbabágurwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbabagurwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Urukundo umuntu akunda undi rugatuma adashyira umutima hamwe","amour très vif","Affection"
            ]
    },
    
    "rubabi": {
        "umuzi/root": "babi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubabi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubabi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'igishyimbo","Variété de haricot","Variety of bean"
            ]
    },
    "kibabo": {
        "umuzi/root": "bábo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibábo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Urwagwa bavanga n'isukari bagacanira mbere yo gutara","Jus de banane qu’on mélange avec du sucre et qu’on fait bouillir avant la fermentation.","Banana juice mixed with sugar and boiled before fermentation."
            ]
    },
    
    "rubaga": {
        "umuzi/root": "baagá",
        "basoma/phonetics": {
            " ": "NA",
        "mu buke/singular": "rubaagá",
        "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikintu cy'ikigome cyane", "très méchante.", "Very mean"  
        ]
    },
    "kabaga": {
        "umuzi/root": "baagá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabaagá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'icyatsi cyeruruka gikebana kiba mu kabande", "Espèce d’herbe blanchâtre des marais","Species of whitish grass from the marshes"
            ]
    },
    "rubamba": {
        "umuzi/root": "baámba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubaámba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu cg inyamaswa cg ikintu gifite iryo bara", "Être ou objet de couleur noir","Being or object of black color."
            ]
    },
    "kabamba": {
        "umuzi/root": "baámba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabaámba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ikimera", "Espèce de plante non identifiée.","Species of unidentified plant."
            ]
    },
    "kabambare": {
        "umuzi/root": "baambaáre",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabaambaáre",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabambare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ifi yo mu bwoko bw'imikubengeri","Poisson du genre silure","Fish of the catfish type"
            ]
    },
    
    "kabambe": {
        "umuzi/root": "baámbe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabaámbe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabambe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Umuntu cg ikintu bihebuje mu miterere, mu mikorere cg mu myifatire", "Personne d'excellence","Person who excels in a particular field."
            ]
    },
   
    "mibambwe": {
        "umuzi/root": "báambwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mibáambwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mibambwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Rimwe mu mazina y'ubwami bw'ingoma nyiginya","Non royal de la dynastie nyiginya","One of the dynastic names of the kings"
             ]
    },
    "rubanda": {
        "umuzi/root": "baanda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubaanda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubanda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu uwo ari we wese mudafitanye isano","Personne avec qui l’on n’a pas de relations","any person with whom one has no relations."
            ]
    },
    
    "mbandama": {
        "umuzi/root": "baandamá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbaandamá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbandama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu kimase ku kindi","objet qui adhère à ou se couche sur","Being or object that adheres to or lies on"
            ]
    },
    "ibango": {
        "umuzi/root": "báango",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ibáango",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibango",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igiti gisongoye kandi gishise mu ikintu ahasongoye hareba hejuru","Bois taillé en biseau","Wood shaped at an angle"
             ]
    },
    "imbangurane": {
        "umuzi/root": "baángurane",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbaángurane",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbangurane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "impanga zidahuje igitsina","Twins of different sexes","Jumeaux"
            ]
    },
    "mbanji": {
        "umuzi/root": "baanji",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbaanji",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbanji",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara itera inka guhitwa","Diarrhée des vaches","Diarrhea of cows"
            ]
    },
    
    "kibanza": {
        "umuzi/root": "baanza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibaanza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibanza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ingoma y'ingabe ku bwa Mukobanya na Gahima","Tambour dynastique de Mukobanya et de Gahima.","Dynastic drum of Mukobanya and Gahima."
            ]
    },
    
    "mabanza": {
        "umuzi/root": "báanza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mabáanza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mabanza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi uri mu burengerazuba bwo hagati bwa perefegitura ya Kibuye wahaye izina komini uri mo","Colline et commune situées au centre ouest de la préfecture de Kibuye.","Hill and municipality located in the central-west of the Kibuye prefecture."
            ]
    },
   
    "rubara": {
        "umuzi/root": "bára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu ufite urubara","Surnom de qui a une tache accidentelle sur la peau","Nickname for someone with an accidental mark on the skin."
            ]
    },
    "mbaraga": {
        "umuzi/root": "baragá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbaragá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbaraga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu udashaka umugore","Homme qui ne veut pas se marier","Man who does not want to marry"
            ]
    },
    "kabaragara": {
        "umuzi/root": "baragará",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabaragará",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabaragará",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
            "ubwo bw'igitoki kivamo imineke. kamaramasenge","Variété de bananier","variety of banana"
                ]
    },
    "imbaragure": {
        "umuzi/root": "barágure",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbarágure",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbaragure",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibintu byisatura kubera ubushyuhe ", "Grains qui sortent des gousses sous l’effet de la chaleur","Seeds that come out of the pods under the effect of heat"
             ]
    },
    "rubarambavu": {
        "umuzi/root": "barambavu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubarambavu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubarambavu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ingabo igira ingusho","Guerrier dont le coup est mortel","Warrior whose strike is deadly"
            ]
    },
    "mbarara": {
        "umuzi/root": "barara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbarara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbarara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'igishyimbo cyaraturutse mu Nkore i Mbarara.","Espèce de haricots venue de Mbarara","A species of beans from Mbarara"
            ]
    },
    "imbare": {
        "umuzi/root": "bare",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbare",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'inzoka","sorte de serpent","species of a snake"
            ]
    },
    
    "imbare": {
        "umuzi/root": "baré",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbaré",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amenyo y'imbare","Dents fort espacées","Teeth widely spaced"
            ]
    },
    "bibari": {
        "umuzi/root": "bari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bibari",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bibari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu ufite umunwa wasadutse","Surnom de qui a un bec","Nickname for someone with a beak"
            ]
    },
    "imbari": {
        "umuzi/root": "bári",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbári",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igice cy'inzu kiri ku ruhande rw'inyuma y'iziko", "Partie de la maison située derrière le foyer.","Part of the house located behind the hearth."
            ]
    },
    
    "mbarirano": {
        "umuzi/root": "bárirano",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbárirano",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbarirano",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inkuru mbarirano ni inkuru utahagazeho","Nouvelle qu’on connaît pour l’avoir entendue","News that one knows from having heard it"
            ]
    },
    "rubariro": {
        "umuzi/root": "báriro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubáriro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubariro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Intango nini cyane","Cruche géante.","Giant jug"
            ]
    },
    "mbarwa": {
        "umuzi/root": "barwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbarwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbarwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibintu cg abantu bake cyane", "peu nombreux.","Few"
            ]
    },
    "mbasha": {
        "umuzi/root": "bashá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbashá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbasha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwe mu basirikare bakuru b'abadage","Officier militaire du temps de la colonisation allemande.","Military officer from the time of German colonization."
            ]
    },
    "mbatama": {
        "umuzi/root": "batamá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbatamá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbatama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ibiryo byikanze gushirira bigafata mu ndiba y'inkono","Aliments presque brûlés qui adhèrent au fond de la marmite.","Almost burned foods that stick to the bottom the pot."
            ]
    },
    
    "rubavu": {
        "umuzi/root": "bavu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubavu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubavu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burengerazuba bwa ruguru bwa perefegitura ya Gisenyi ukaba warahaye izina komini uri mo kandi ni wo wubatse mo umurwa w'iyo perefegitura", "Colline et commune du nord","Hill and municipality of the north"
             ]
    },
    "rubaya": {
        "umuzi/root": "baya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubaya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubaya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu munini cyane","Homme très gros", "Very fat man"
            ]
    },
    "kabaya": {
        "umuzi/root": "baya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabaya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabaya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Gaseke wahaye izina superefegitura uri mo iyo superefegitura igizwe n'amakomini Gaseke Giciye na Karago.","NONE","NONE"
            
        ]
    },
    "kibayi": {
        "umuzi/root": "báayi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibáayi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibayi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu majyepfo ya perefegitura ya Butare wahaye izina Komini uri mo","Colline et commune du Sud de la préfecture de Butare.", "Hill and municipality in the south of the Butare prefecture"
             ]
    },
    
    "mbazi": {
        "umuzi/root": "bázi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbázi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri perefegitura ya Butare hagati kandi ukaba warahaye izina komini uri mo", "Colline et commune situées au centre de la préfecture de Butare.","Hill and municipality located in the center of the Butare prefecture" 
            ]
    },
    "akabazo": {
        "umuzi/root": "bázo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akabázo",
            "mu bwinshi/plural": "utubázo"
        },
        "bandika/writing": "akabazo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " akamenyetso bashyira inyuma y'interuro ibaza","Point d’interrogation","question mark"
            ]
    },
    "mbeba": {
        "umuzi/root": "beba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbeba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbeba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini ya Nyamabuye muri perefegitura ya Gitarama","Colline de la commune de Nyamabuye dans la préfecture de Gitarama.", "Hill of the municipality of Nyamabuye in the Gitarama prefecture"
            ]
    },
    "rubebe": {
        "umuzi/root": "beébe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubeébe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubebe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "intabwirwa","Désobéissant","Disobedient"
            ]
    },
    "mabya": {
        "umuzi/root": "mabya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mabya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mabya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu ufite amabya y'ibitenga", "Surnom donné à une personne qui a de gros testicules", "ballsy"
            ]
    },
    "imbebya": {
        "umuzi/root": "bebyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbebyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbebya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igitinyiro kigaragara mu maso", "Respect qu’on témoigne par le regard","Respect that is shown by lowering one's gaze" 
            ]
    },
    "kibeho": {
        "umuzi/root": "bého",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibého",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibeho",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu majyaruguru ya komini Mubuga muri perefegitura Gikongoro wahaye izina paruwasi gatorika iwubatse ho","Colline et paroisse catholique situées dans la partie nord de la commune de Mubuga dans la préfecture de Gikongoro.","Hill and Catholic parish located in the northern part of the municipality of Mubuga in the Gikongoro prefecture"
             ]
    },
    "imbekane": {
        "umuzi/root": "beékane",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbeékane",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbekane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Uguhigana kw'abantu banganye","Hostilité réciproque.","Mutual hostility"
            ]
    },
    "imbetezi": {
        "umuzi/root": "bétezi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbetezi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibiheri by'amakoma bashyira mu mutobe kugira ngo uzabire urwagwa rushye", "Farine grossière de sorgho non trempé qu’on met dans le jus de banane pour la fermentation.","unsoaked sorghum flour that is added to banana juice to facilitate fermentation" 
            ]
    },
    "mbiburi": {
        "umuzi/root": "biburi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbiburi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbiburi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ifi iboneka muri Rusizi","Espèce de poisson de la rivière Rusizi","Species of fish from the Rusizi River" 
             ]
    },
    "rubika": {
        "umuzi/root": "biká",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubiká",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubika",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba isake","Surnom du coq", "Nickname of the rooster"
             ]
    },
    "kibindamahururu": {
        "umuzi/root": "biindamahururu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibiindamahururu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibindamahururu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu waheranije mu gusambana","Surnom d’un grand coureur de femmes","Nickname of a great womanizer"
            ]
    },
    "kamisa": {
        "umuzi/root": "misa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kamisa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamisa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu ukunda gusabiriza inzoga", "Surnom du quémandeur de bière.", "Nickname of the beer beggar"
            ]
    },
    "urubingo": {
        "umuzi/root": "biingo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubiingo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubingo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikimera kirekire kiba mu bishanga n'inkengero z'imigezi ","Grande plante vivace de type roseau","reed"
            ]
    },
    "imbirayuungwe": {
        "umuzi/root": "birayuungwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbirayuungwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbirayungwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubushyuhe bwinshi bw'umwuka", "Forte chaleur atmosphérique","humidity"
            ]
    },        
    "kibirira": {
        "umuzi/root": "birira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibirira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibirira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi uri mu majyepfo ya perefegitura ya Gisenyi wahaye izina komini uri mo","Colline et commune situées dans le Sud de la préfecture de Gisenyi.", "Hill and commune located in the south of the Gisenyi prefecture" 
            ]
           
    },
    "mbirirwa": {
        "umuzi/root": "birirwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbirirwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbirirwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibiryo byo mu nkono hejuru","Partie des aliments qui se trouve vers le dessus de la marmite.","Part of the food that is located towards the top of the pot"
            ]
            
    },
    
    "urubito": {
        "umuzi/root": "biito",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urubiito",
            "mu bwinshi/plural": "imbiito"
        },
        "bandika/writing": "rubito",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "inkoni cg igiti gisongoye","Pieu taillé en pointe","Stake sharpened to a point"
            ]
    },
    "imbizi": {
        "umuzi/root": "bizi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbizi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbizi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ntibajya imbizi. Ntibumvikana","qui ne s'entendent pas","not getting along. incompatible"
            ]
    },
    "imboga": {
        "umuzi/root": "bogá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbogá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imboga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ibibabi cg imiteja cg indabyo by'ibimera biribwa ibyo ari byo byose","Feuilles gousses ou fleurs comestibles", "Edible leaves"
            ]
    },
    "imbogamizi": {
        "umuzi/root": "bogamizi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbogamizi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbogamizi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyica amahirwe ikintu icyo ari cyo cyose kibuza umuntu gukora cg kugera ku cyo yashakaga", "Empêchement", "obstacle"
            ]
    },
    "intego": {
        "umuzi/root": "tégo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "intégo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "intego",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
            "intumbero","objectif","goal"
        ]
    },
    "kibombwe": {
        "umuzi/root": "boombwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kiboombwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibombwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'umwumbati","Variété de manioc","Variety of cassava"
            ]
    },
    "imbonanya": {
        "umuzi/root": "bonánya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbonánya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbonanya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Kurega umuntu umuvuga ibiri ukurí wabyiboneye"," Porter une accusation exacte en tant que témoin oculaire","accusation as eyewitness"
            ]
        
    },
    "imbonekerabusa": {
        "umuzi/root": "bonekerabusa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbonekerabusa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbonekerabusa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu ubona utagotse","Ce qu’on gagne sans peine.","What one gains without effort"
            ]
    },
    "kiborerwa": {
        "umuzi/root": "borérwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kiborérwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kiborerwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu usinda vuba","Pers qui s’enivre facilement","lightweight"
            ]
    },
    
    "rubuci": {
        "umuzi/root": "buci",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubuci",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubuci",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ufite inda imeze ityo","Surnom d’une personne qui a un gros ventre affaissé.", "Nickname for a person with a large sagging belly"
            ]
    },

    "kibugenza": {
        "umuzi/root": "bugeenzá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibugeenzá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibugenza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inyamaswa y'inkaka ikunda kugenda imbere y'izindi", "Animal hardi qui marche toujours à la tête du troupeau.","Brave animal that always walks at the head of the herd"
            ]
    },
    "imbugu": {
        "umuzi/root": "bugu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbugu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbugu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoya bukikije ibere ry'umugabo","Poils voisins du mamelon d’un homme.","Hairs near a man's nipple"
            ]
    },

    "kabunga": {
        "umuzi/root": "buungá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabuungá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabunga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "akazina baha umuntu ubunga ","Surnom du vagabond","A common nickname for a vagabond"
            ]
    },
    
    "imbungiramihigo": {
        "umuzi/root": "buungiramihigo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbuungiramihigo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbungiramihigo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umutwe w'intore za Kayondo ka Mbanzabigwi watwaraga Ubusanza ahegereye mu wa","Troupe de cadets de Kayondo fils de Mbanzabigwi ancien chef du Busanza vers les années ", "Troop of cadets of Kayondo, son of Mbanzabigwi, former chief of Busanza around the years"
            ]
    },
    
    "imburi": {
        "umuzi/root": "buuri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbuuri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imburi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu cyujurije kandi kiremereye","Chose dense et pesante"," dense and heavy"
            ]
    },
    "mburugu": {
        "umuzi/root": "burugu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mburugu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mburugu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara yanduza ikomoka ku busambanyi ikaba yashahura umuntu","maladie sexuellement transmissible","sexually transmitted disease"
            ]
    },
    "imbusane": {
        "umuzi/root": "busáne",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imbusáne",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imbusane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ku buryo butagiye umujyo umwe", "De façon non uniforme.", "In a non-uniform manner"
            ]
    },
     "kibuye": {
        "umuzi/root": "buye",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kibuye",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kibuye",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burengerazuba bw'urwanda ku nkengero z'ikivu Wahaye izina perefegitura uri mo.",
        
        ]
    },
    "rubwa": {
        "umuzi/root": "bwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwoko bw'umukenke","Variété de l’herbe", "Variety of grass"
            ]
    },
    "mbiruma": {
        "umuzi/root": "zirumá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mbirumá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mbiruma",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'insina yera igitoki cy'inyamunyo","Variété de bananier produisant des bananes à cuire","Variety of banana plant producing cooking bananas"
            ]
    },
    "kabwera": {
        "umuzi/root": "bweerá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kabweerá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kabwera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "indaya","prostituée","prostitute"
            ]
    },
    "rubya": {
        "umuzi/root": "bya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rubya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rubya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikabutura y'impanurano itari igipimo cy'umuntu ikamusaguka","Culotte achetée toute faite dont les mesures sont trop grandes","Pre-made shorts whose measurements are too large"
            ]
    },
    
    "gica": {
        "umuzi/root": "cá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gicá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gica",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Rwabuze gica. ibintu byananiranye","En parlant d’une situation, être inextricable","extremely complicated"
            ]
    },
    "rucabagome": {
        "umuzi/root": "cáabagomé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rucáabagomé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rucabagome",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'imwe mu ngoma z'ibwami","Nom d’un des tambours dynastiques","Name of one of the dynastic drums"
            ]
    },
    "incabari": {
        "umuzi/root": "cabari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "incabari",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "incabari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imyambaro ishaje yacikaguritse", "Habits très usés","Very worn clothes"
            ]
    },
    "inshabintu": {
        "umuzi/root": "cáabiintu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "íinshabintu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshabintu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikintu gishobora gutuma ibintu bidogera","Méchant dangereux","Mean dangerous" 
            ]
    },
    "umucaca": {
        "umuzi/root": "caáca",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gacaáca",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umucaca",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'icyatsi kirandaranda ku butaka amatungo agakunda kukirisha","Espèce d’herbe gazonnante et rampante très appréciée des animaux domestique","A species of creeping, turf-forming grass highly appreciated by domestic animals."
            ]
    },
    "gacacuzi": {
        "umuzi/root": "cáacuuzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gacáacuuzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gacacuzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "imbega","souris","mouse"
            ]
    },
    
    "inshaka": {
        "umuzi/root": "caka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "incaka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibintu by'amoko anyuranye kandi binyanyagiye","Multitude d’objets différents et éparpillés","Multitude of different and scattered"
            ]
    },
    "gucakara": {
        "umuzi/root": "cakára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gucakara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gacakara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            [
                "gukora imirimo ya kija. kubungabunga","Être assujetti à des travaux serviles","To be subjected to servile labor"
            ]
        ]
    },
    "umucakara": {
        "umuzi/root": "cakára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umucakára",
            "mu bwinshi/plural": "abacakára"
        },
        "bandika/writing": "umucakara",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
                "ukora imirimo y'agahato","esclave","slave"
        ]
    },
    "inshansha": {
        "umuzi/root": "caánsha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inshaánsha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshansha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inyama bakataguye mo udutongo dutoduto cyane","Viande découpée en tout petits morceaux viande hâchée.", "Meat cut into very small pieces"
            ]
    },
    "inshakara": {
        "umuzi/root": "cakára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inshakara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshakara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'igitoki","Espèce de bananier qui produit des bananes à cuire","banana species"
            ]
    },
    "gacanyamiryango": {
        "umuzi/root": "caanyamiryaango",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gacaanyamiryaango",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gacanyamiryango",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu uzimura cg uteranya abandi","Surnom de celui qui sème la discorde entre les amis.","Nickname for someone who sows discord among friends"
            ]
    },
    
    "bucece": {
        "umuzi/root": "cecé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bucecé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bucece",
        "icyiciro/pos": [
            "adverb",
            "umugereka"
        ],
        "igisobanuro/meaning": [
            
            "utavuga","en silence","in silence"
            ]
    },
    "inshenga": {
        "umuzi/root": "ceénga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "insheénga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshenga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ibisigazwa biboneka nyuma yo kuyungurura","Fragments qui restent après tamisage","Fragments that remain after sieving"
            ]
    },
    "inshenshu": {
        "umuzi/root": "ceénshu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "insheénshu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshenshu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "utujumba duto cg inkodo zabyo","Patates douces trop peu développés", "Sweet potatoes or other underdeveloped tubers considered as waste"
            ]
    },
    
    "rucinya": {
        "umuzi/root": "cinya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rucinya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rucinya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'amasaka akunda kwera mu turere tumwe na tumwe two mu majyaruguru y'urwanda","Variété de sorgho cultivée dans certaines régions septentrionales du Rwanda","Variety of sorghum grown in certain northern regions of Rwanda"
            ]
    },
    "nshiciri": {
        "umuzi/root": "ciiri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nshiiciiri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nshiciri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugezi uri mu majyepfo ya perefegitura ya Gikongoro wahaye izina komini uri mo","Rivière et commune du sud de la préfecture de Gikongoro.", "River and commune in the southern part of the Gikongoro prefecture"
            ]
    },
    
    "giciye": {
        "umuzi/root": "ciiyé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "giciiyé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "giciye",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugezi wo mu burasirazuba bwa perefegitura ya Gisenyi wahaye izina komini uri mo","Rivière et commune à l’Est de la préfecture de Gisenyi.","River and commune in the East of the Gisenyi prefecture"
            ]
    },
    
    "inshogamihana": {
        "umuzi/root": "inshoogamihana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inshoogamihana",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshogamihana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ukunda kuzerera mu mihana cyane", "Personne qui aime fréquenter ses voisins.", "A person who enjoys socializing with their neighbors" 
            ]
    },
    "inshogozabahizi": {
        "umuzi/root": "inshoogozabahizi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inshoogozabahizi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inshogozabahizi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umutwe w'intore za Musinga","Troupe de cadets du roi Musinga","Troop of cadets of King Musinga"
            ]
    },
    "agacubiro": {
        "umuzi/root": "cubiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agacubiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agacubiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "saa sita z'ijoro","minuit","midnight"
            ]
    },
    "igicucu": {
        "umuzi/root": "cúucu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "igicúucu",
            "mu bwinshi/plural": "ibicúucu"
        },
        "bandika/writing": "igicucu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu utazi gutekereza neza. Ahantu hatagera izuba","imbécile.ombre","idiot.shade"
            ]
    },
    
    "agacuho": {
        "umuzi/root": "cuuho",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agacuuho",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agacuho",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umunaniro uhageze umuntu aterwa n'urugendo cg n'imirimo myinshi","Très grande fatigue épuisement","Very great fatigue or exhaustion"
            ]
    },
    "gacukumbuzi": {
        "umuzi/root": "cukuumbuzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gacukuumbuzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gacukumbuzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ushaka iteka kumenya umuzi n'umuhamuro wa buri ikintu","Personne qui cherche toujours à savoir le pourquoi des choses.","person who always seeks to understand the reasons behind things"
            ]
    },
    
    "bucura": {
        "umuzi/root": "curá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bucurá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bucura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwana wese wavutse nyuma y'abo bavukana bose","le dernier-né","last born"
            ]
    },
    "gicurasi": {
        "umuzi/root": "curáasi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gicuráasi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gicurasi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwezi kwa cyenda k'umwaka wa kinyarwanda","Neuvième lunaison de l’année traditionnelle.", "Ninth lunar month of the traditional year"
                
            ]
    },
    
    "gacwira": {
        "umuzi/root": "cwiirá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gacwiirá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gacwirá",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu unywa itabi cyane","grand fumeur","smoker"
            ]
    },
    "gucya": {
        "umuzi/root": "cyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gucyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gucya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ijoro rirangiye.kuvaho umwanda","Faire jour","to dawn. To become clean"
            ]
    },
    
    "rudahakanirwa": {
        "umuzi/root": "dáhakánirwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rudáhakánirwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rudahakanirwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu bahakanira cg bima ikintu ntashirwe ahubwo agakomeza gusaba","Personne à qui on refuse qqch et qui insiste","A person who insists after rejection"
            ]
    },
    "rudahigwa": {
        "umuzi/root": "dáhigwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rudáhigwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rudahigwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami wa kabiri w'urwanda ushingiye ku bucurabwenge ukabara usubira inyuma ","Deuxième roi du Rwanda selon la généalogie","Second king of Rwanda according to genealogy"
            ]
    },
    "kadahwema": {
        "umuzi/root": "dáhweemá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kadáhweemá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kadahwema",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu uba akora igihe cyose ataruhuka","Surnom donné à une personne qui est toujours occupée", "Nickname given to a relentless person" 
            ]
    },
    "kidakoreka": {
        "umuzi/root": "dákoréka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kidákoréka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kidakoreka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'intabwirwa","Personne têtue.","Stubborn person"
            ]
    },
    
    "kudara": {
        "umuzi/root": "dári",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kudára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kudara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "kunanuka bikabije","Maigrir fort","lose weight drastically"
            ]
    },
    
    "mudasigwa": {
        "umuzi/root": "dásigwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mudásigwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mudasigwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu uzi guca hasi agakurikirana ibye","Personne qui poursuit avec persévérance.","A person who pursues with perseverance"
            ]
    },
    "mudasomwa": {
        "umuzi/root": "dásomwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mudásomwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mudasomwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugezi wo mu burengerazuba bwa perefegitura ya Gikongoro wahaye izina komini unyura mo", "Rivière située à l’ouest de la préfecture de Gikongoro et commune dans laquelle elle coule.", "River located to the west of the Gikongoro prefecture and the municipality through which it flows" 
            ]
    },
    "mudatuza": {
        "umuzi/root": "dátuuzá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mudátuuzá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mudatuza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu utava ku izima","personne qui ne lâche pas","relentless person"
            ]
    },
    "rudede": {
        "umuzi/root": "dede",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rudede",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rudede",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "rukumbi","unique","unique"
            ]
   
    },
    
    "kadende": {
        "umuzi/root": "deénde",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kadeénde",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kadende",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igikoresho kimeze nk'igurudumu bakomanga kikarangira","object de forme circulaire ressemblant plus ou moins à la jante d’une roue de voiture.","object somewhat resembling the rim of a car wheel"
            ]
    },
    
    "rudenge": {
        "umuzi/root": "deénge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rudéenge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rudenge",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amazi y'ibiziba","Eau boueuse.","Muddy water"
            ]
    },
    
    "kidobya": {
        "umuzi/root": "dobyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kidobyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kidobya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ukunda guteranya abandi","Semeur de brouille de discorde","who sows discord"
            ]
    },
    "ukadomagure": {
        "umuzi/root": "domágure",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akadomágure",
            "mu bwinshi/plural": "utudomágure"
        },
        "bandika/writing": "akadomagure",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Utudomo tw'utwenge cg utunogo cg utubara tugaragara tuba ku ikintu","Petits trous ou petites taches apparents.","Small holes" 
            ]
    },
    "rudori": {
        "umuzi/root": "dori",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rudori",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rudori",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "rukumbi","unique","unique"
            ]
    },
    "rudugira": {
        "umuzi/root": "duugiira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruduugiira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rudugira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inyamaswa inanutse idafite intege", "Personne maigre et faible","skinny person"
            ]
    },
    "ruduha": {
        "umuzi/root": "duuha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruduuha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruduha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bita umuntu w'umubeshyi waheranije","Surnom d’un grand menteur", "Nickname of a great liar"
            ]
    },
    "buduriya": {
        "umuzi/root": "duriyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buduriyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buduriya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'agacuma ka kizungu gakoze mu ikintu kimeze nk'icyuma gisengesheje umwenda worohereye","Gourde de type importé faite d’aluminium et couverte de tissu léger.", "Imported type water bottle made of aluminum and covered with lightweight fabric" 
            ]
    
    },
   
    "akebo": {
        "umuzi/root": "éebo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akéebo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "akebo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "agakoresho babikamo imyaka","Petit panier","small basket"
            ]
    },
    
    "ubwege": {
        "umuzi/root": "eege",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubweege",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwege",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ugutitiriza ushaka ikintu", "Insistance pour obtenir qqch.", "Insistence to obtain something"
            ]
    },
    "rwego": {
        "umuzi/root": "éego",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwéego",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwego",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "intebe yegamirwa kandi izingwa", "Chaise pliante.", "Folding chair"
            ]
    },
    "ubwehe": {
        "umuzi/root": "eéhe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubweéhe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwehe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Impamvu y'ibanze intandaro y'ibyago","Cause principale d’un malheur.","Main cause of a misfortune" 
            ]
    },
    "cyehe": {
        "umuzi/root": "eehé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyeehé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyehe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umupfayongo","sot","stupid"
            ]
    },
    "rwema": {
        "umuzi/root": "eemá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rweemá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwema",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "intwari idasubira inyuma urugamba ruhinanye","Guerrier vaillant ","great warrior"
            ]
    },
    "ubwema": {
        "umuzi/root": "éemá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwema",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwema",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuba umuntu ahagaze cg agenda yemye","droiture","Upright position of a person"
            ]
    },
    "urwemangabo": {
        "umuzi/root": "éemangabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwéemangabo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwemangabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akajugane kabuza umuntu kuruhuka","Activité ininterrompue manque de repos","Uninterrupted activity lacks rest" 
            ]
    },
    
    "abemera": {
        "umuzi/root": "eémera",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "abeémera",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "abemera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Abigishwa bo mu gice cya kabiri","Catéchumènes du deuxième cycle.", "Catechumens of the second cycle" 
            ]
    },
    "ubwemere": {
        "umuzi/root": "eémere",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubweémere",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwemere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "uruhushya","permission","permission"
            ]
    },
    "amena": {
        "umuzi/root": "eena",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ameena",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amena",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ndabyemera","amen","amen"
            ]
    },
    "icyenda": {
        "umuzi/root": "eendá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyeendá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyenda",
        "icyiciro/pos": [
            "number",
            "umubare"
        ],
        "igisobanuro/meaning": [
            
                "umubare ukurikira umunane","neuf","nine"
            ]
    },
    
    "amenda": {
        "umuzi/root": "éenda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "améenda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amenda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amarira y'igisebe","Matière visqueuse qui se dégage des plaies sérum.","watery substance that comes from wounds"
            ]
    },
    "amende": {
        "umuzi/root": "éende",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "améende",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amende",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amazi yikeneka mu mata","Sérum du lait","whey"
            ]
    },
    "ubwende": {
        "umuzi/root": "eénde",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubweénde",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwende",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubushake","volonté","willingness"
            ]
    },
    
    "rwenderi": {
        "umuzi/root": "eenderi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rweenderi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwenderi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " umugore w'ikinyamwanda","Femme très sale", "Very dirty woman"
            ]
    },
    "imyendezo": {
        "umuzi/root": "eendezo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imyeendezo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imyendezo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Intangiriro cg inkomoko y'ikintu","point de départ commencement origine cause.","Beginning"
            ]
    },
    "mwendo": {
        "umuzi/root": "eendo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mweendo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mwendo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burasirazuba bwa perefegitura ya Kibuye wahaye izina ikomini uri mo", "Colline et commune situées dans la partie orientale de la préfecture de Kibuye.","Hill and municipality located in the eastern part of the Kibuye prefecture" 
            ]
    },
    "umwene": {
        "umuzi/root": "éene",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwéene",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwene",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuyaga wo mu Kivu uhuha uturuka mu Bugonde ugana ku ijwi", "Vent du lac Kivu qui souffle de Bugonde vers l’île d’Ijwi.", "Wind from Lake Kivu blowing from Bugonde towards Ijwi Island"
            ]
    },
    
    "ubwenge": {
        "umuzi/root": "éenge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwéenge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwenge",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubushobozi buteye ukwabwo buba muri kamere muuntu butuma buri wese mu rugero rwe atekereza","intelligence","intelligence"
            ]
    },
    "menge": {
        "umuzi/root": "éenge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "méenge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "menge",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "kuba menge","Ne pas dormir","awake"
            ]
    },
    "urwenge": {
        "umuzi/root": "éenge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwéenge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwenge",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwitonzi bwa cyane", "Grande sagesse", "Great wisdom"
            ]
    },
    
    "ruhimbi": {
        "umuzi/root": "ruhiimbi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhiimbi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhimbi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umukobwa ujijutse w'umunyamutima", "Surnom donné à une fille qui a un esprit ouvert", "Nickname given to a girl who has an open mind"
            ]
    },
    "mwabo": {
        "umuzi/root": "mwaábo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mwaábo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mwabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu wikunda by'agakabyo","Surnom donné à un égoïste", "Nickname given to an egoist"
                
            ]
    },
    
    "rurahonya": {
        "umuzi/root": "rurahonya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rurahonya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rurahonya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'inyaryenge ariko ukaba utabimukekera ho", "Personne  très maligne sans en avoir l’air.","Someone who clever without seeming so"
            ]
    },
    "ubwatwa": {
        "umuzi/root": "twá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwatwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwatwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubugoryi","Idiotie","Idiotism "
            ]
    },
    "umwenjya": {
        "umuzi/root": "éenjyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwéenjyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwenjya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "inzika","rancune","grudge"
            ]
    },
    "urwenya": {
        "umuzi/root": "éenyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwéenyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwenya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikiganiro kiryoshye kandi gisekeje","plaisanterie","joke"
            ]
   
    },
    "amenyo": {
        "umuzi/root": "éenyo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "iryíinyo",
            "mu bwinshi/plural": "améenyo"
        },
        "bandika/writing": "amenyo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "amagufwa amera mu ishinya","dents","teeth"
            ]
    },
    "iyenze": {
        "umuzi/root": "éenzé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "iyéenzé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "iyenze",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuco w'umuntu uhora yanduranya", "Caractère querelleur","Quarrelsome character" 
            ]
       },   

    "amera": {
        "umuzi/root": "eéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ameéra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'umunyu wera cyane","Espèce de sel très blanc.","white salt"
            ]
    },
    "ibyera": {
        "umuzi/root": "eéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ibyeéra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibyera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imyambaro yera umusaseredoti yambara mu gihe cya misa", "Ornements liturgiques blancs portés par le prêtre pour dire la messe.", "White liturgical vestments worn by the priest to celebrate the Mass" 
            ]
    },
    "urwera": {
        "umuzi/root": "eéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urweéra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikoraniro ry'ibintu byera de kandi byiza","Ensemble de ce qui est tout blanc et beau.","A collection of everything that is all white and beautiful" 
            ]
    },
    "ubwera": {
        "umuzi/root": "eéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubweéra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Kwendana mbere y'uko igihe gisanzwe cyo kwirabura kirangira ","rite par laquelle on fait relations sexuelles avec sa femme en clôturant du deuil","rite by which one has sexual relations with one's wife to end the mourning period"
            ]
    },
    "kera": {
        "umuzi/root": "eéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "keéra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ahashize","jadis","in the past"
            ]
    },
    "icyeragati": {
        "umuzi/root": "éeragáti",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyéeragáti",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyeragati",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Gutereranwa ukabura uwo wiyambaza","Être abandonné de tout le monde","to be abandoned by everyone"
            ]
    },
    
    "icyerekezo": {
        "umuzi/root": "éerekezo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyéerekezo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyerekezo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akarere umuntu agana mo cg ikintu giherereye mo","Direction","Direction"
            ]
    },
    
    "urwererane": {
        "umuzi/root": "eérerane",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urweérerane",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwererane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Umweru w'ihabu","Blancheur éclatante.","Dazzling whiteness" 
            ]
    },
    "bwerere": {
        "umuzi/root": "eereére",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bweereér",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bwerere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "kuruhira ubusa", "Echouer malgré tous ses efforts","fail despite efforts"
            ]
    },
    "rwerere": {
        "umuzi/root": "eérere",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rweérere",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwerere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akarere ko mu majyaruguru ya perefegitura ya Gisenyi kahaye izina Komini kari mo","Région et commune du nord de la préfecture de Gisenyi.","Region and municipality in the north of the Gisenyi prefecture"
            ]
    },
    
    "ibyeru": {
        "umuzi/root": "éeru",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ibyéeru",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibyeru",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Impigu y'umuvuzi cg y'utanga impigi","Honoraires payés au guérisseur ou au fabricant d’amulettes.", "Fees paid to the healer or the amulet maker"
            ]
    },
    "urweru": {
        "umuzi/root": "éeru",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwéeru",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urweru",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amazi cg ibintu by'urutotwe byererana","Liquide ou matière pâteuse de couleur blanchâtre.","Liquid or pasty substance of a whitish color"
            ]
    },
    "ubweru": {
        "umuzi/root": "éeru",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwéeru",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubweru",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ahantu h'ishyamba hatari ibiti","Clairière dans la forêt.","Clearing in the forest"
            ]
    },
    
    "cyeru": {
        "umuzi/root": "eéru",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyeéru",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyeru",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu majyaruguru ya perefegitura ya Ruhengeri wahaye izina komini uri mo","Colline et commune situées dans la partie septentrionale de la préfecture de Ruhengeri.", "Hill and municipality located in the northern part of the Ruhengeri prefecture"
            ]
    },
    "ameruza": {
        "umuzi/root": "eéruza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ameéruza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ameruza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amerwe y'agakabyo", "Envie de viande exagérée", "Exaggerated craving for meat"
            ]
    },
    "amerwe": {
        "umuzi/root": "eerwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ameerwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amerwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Irari rikabije ry'inyama","Grande envie de viande", "meat craving"
            ]
    
    },
    "rwesero": {
        "umuzi/root": "eesero",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rweesero",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwesero",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Kagano perefegitura Cyangugu wahaye izina superefegitura uri mo iyo superefegitura igizwe n'makomini Kagano Kirambo na Gatare.","NONE","NONE"
            ]
    },
    
    "umwete": {
        "umuzi/root": "eéte",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umweéte",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwete",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubushishikare ku murimo","Ardeur","Enthusiasm"
            ]
    },
    "urwevu": {
        "umuzi/root": "eévu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urweévu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwevu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ivu ritumuka mu muriro waka", "Cendres légères qui se dégagent d’un feu.","Light ashes that are released from a fire"
            ]
    },
    "rwevu": {
        "umuzi/root": "eévu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rweévu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwevu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bahimba umuntu w'umunyamwanda","Surnom d’une personne sale", "Nickname of a dirty person"
            ]
    },
    "umweya": {
        "umuzi/root": "eeya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umweeya",
            "mu bwinshi/plural": "imyeeya"
        },
        "bandika/writing": "umweya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
            "inkengero y'inkiyaga","Rive d’un lac","lake bank"
            ]
    },
    
    "ibyeyerwa": {
        "umuzi/root": "éeyeerwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ibyéeyeerwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibyeyerwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibintu by'insigarira kandi bike cyane","Résidu minime", "Minimal residue" 
            ]
    },
    "icyeyi": {
        "umuzi/root": "eeyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyeeyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyeyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikimwaro","honte","shame"
            ]
    },
    "imeza": {
        "umuzi/root": "éezá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "iméezá",
            "mu bwinshi/plural": "améezá"
        },
        "bandika/writing": "ireza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "igikoresho baterekaho","table","table"
            ]
    },
    "icyeza": {
        "umuzi/root": "eéza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyeéza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyeza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikintu kireshya","Attrait","attraction"
            ]
   
    },
    "urwezamahembe": {
        "umuzi/root": "éezamáheémbe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwéezamáheémbe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwezamahembe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inka ifite amahembe yera kandi maremare ikagira n'umubyimba mwiza uringaniye","Vache qui a de longues cornes blanches et dont la taille est bien proportionnée","Cow with long white horns and a well-proportioned size"
            ]
    },
    "rwezamariba": {
        "umuzi/root": "eezamariba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rweezamariba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwezamariba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imfizi y'ikirangabwami y'umwami Rwabugiri","Taureau de règne du roi Rwabugiri.","Bull of the reign of King Rwabugiri"
            ]
    },
      
    "imyezi": {
        "umuzi/root": "éezi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imyéezi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imyezi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igihe cg iminsi yose ukwezi kumara kumurika","Partie du mois lunaire où la lune est visible","Part of the lunar month when the moon is visible"
            ]
    },
    "mwezi": {
        "umuzi/root": "éezi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mwéezi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mwezi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu majyepfo ya komini Karengera","Colline et paroisse situées dans la partie sud commune Karengera","Hill and parish located in the southern part in Karengera municipality"
            ]
    },
    "kwezi": {
        "umuzi/root": "éezi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kwéezi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kwezi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ubwoko bw'ikijumba budatinda kwera","Variété de patate douce","Variety of sweet potato."
            ]
    },

    "gifaru": {
        "umuzi/root": "faáru",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gifaáru",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gifaru",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'uburozi bw'ubufuterano","Espèce de sortilège.","Type of spell"
            ]
    },
    "gafashi": {
        "umuzi/root": "fáshi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gafáshi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gafashi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ikimera", "Espèce de plante non identifiée","Species of unidentified plant"
            ]
    },
    "imfatirizo": {
        "umuzi/root": "fátirizo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imfátirizo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imfatirizo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Udukwi tw'udushari bakoresha kugira ngo dufatishe izindi", "Petit bois employé pour faire prendre le feu", "Small wood used to start a fire"
            ]
    },
    "mafubo": {
        "umuzi/root": "fubo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mafubo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mafubo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ukugoboka mu mirimo cg ugufasha akagukura mu bizazane","Personne altruiste dévouée qui se dépense pour les autres", "Selfless person who dedicates themselves to helping others"
            ]
    
    },
    
    "rugaba": {
        "umuzi/root": "gabá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugabá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugaba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bitirira Imana","Dieu", "nickname to refer to God"
            ]
    },
    "rugabagaba": {
        "umuzi/root": "gáabagáaba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruggáabagáaba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugabagaba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu muremure by'agakabyo", "Surnom d’une personne excessivement grande.", "Nickname for an excessively tall person."
            ]
    },
    "rugabano": {
        "umuzi/root": "gabano",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugabano",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugabano",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Bwakira","Nom d’une colline située dans la commune de Bwakira.","Name of a hill located in the municipality of Bwakira"
            ]
          
    },
    "magabari": {
        "umuzi/root": "gabari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugabari",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "magabari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'udushyimbo duto twirabura", "Variété de petits haricots noirs.","Variety of small black beans."
            ]
    },
    "rugabishabirenge": {
        "umuzi/root": "gabiishabireenge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugabiishabireenge",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugabishabirenge",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "rugabishabirenge","Personne généreuse à l’excès","too generous"
            ]
    },
    "umugabo": {
        "umuzi/root": "gabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umugabo",
            "mu bwinshi/plural": "abagabo"
        },
        "bandika/writing": "gabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikinyuranyo cy'umugore","homme","male"
                
            ]
    },
    "mugabo": {
        "umuzi/root": "gabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugabo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bahimba ingwe kubera ko itihinda","Surnom donné au léopard parce qu’il est audacieux.","Nickname given to the leopard because it is bold."
            ]
    },
    
    "bagabobararya": {
        "umuzi/root": "bararyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bagabobararyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bagabobararya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'insina cg igitoki yera","Variété de bananier","Variety of banana plant"
            ]
    },
    "mugabuhanda": {
        "umuzi/root": "uháanda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muubauháanda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugabuhanda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu utinyitse", "Surnom d’une personne redoutable", "Nickname of a formidable person."
            ]
    },
    "mugabuzi": {
        "umuzi/root": "gabuzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugabuzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugabuzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akagufa gasuma mu gituza aho imbavu zihurira", "Appendice xiphoïde","Xiphoid process"
            ]
   
    },
    
    "bugagara": {
        "umuzi/root": "gagára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bugagára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bugagara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu wagagajwe n'imbeho", "Surnom d’une pers engourdie par le froid.", "Nickname of a person numbed by the cold"
            ]
        },
    "rugahura": {
        "umuzi/root": "gahura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugahura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugahura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bita umuntu w'umunyamwaga","Surnom d’une pers très dure qui manque de cœur d’humanité","Nickname for a person who lacks compassion"
            ]
    },
   
    "mugambazi": {
        "umuzi/root": "gaambaazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugaambaazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugambazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burengerazuba bwa perefegitura ya Kigali","Colline de l’ouest de la préfecture de Kigali", "Hill in the west of the Kigali prefecture"
            ]
    },
    "mugambira": {
        "umuzi/root": "gaambira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugaambira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugambira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Mu migani ijambo rivuga inkokokazi",  "Poule dans le langage des contes","hen in poetic language"
            ]
    },
    "bugambira": {
        "umuzi/root": "gaambira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bugaambira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bugambira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Kabarondo", "Colline de la commune de Kabarondo","Hill in the Kabarondo municipality"
            ]
    },
    "magambo": {
        "umuzi/root": "gaambo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "magaambo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "magambo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ifi","Espèce de poisson non identifié", "Species of unidentified fish"
            ]
    },
    "rugambwa": {
        "umuzi/root": "gaambwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugaambwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugambwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w 'ikirangirire","Homme célèbre","Famous person"
            ]
    
    },
    
    "rugande": {
        "umuzi/root": "gaandé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugaandé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugande",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'imyumbati", "Variété de manioc","Variety of cassava"
            ]
    },
   
    "muganga": {
        "umuzi/root": "gaanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugaanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muganga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'isabune","Espèce de savon", "Type of soap"
            ]
    },
    "umuganga": {
        "umuzi/root": "gaanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umugaanga",
            "mu bwinshi/plural": "abagaanga"
        },
        "bandika/writing": "umuganga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu uvura","agent médical", "medical person"
            ]
    },
    "amaganga": {
        "umuzi/root": "gaanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amagaanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amaganga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "inkari z'inyamazwa","urine des ruminants","urine of ruminants"
            ]
    },
    "maganga": {
        "umuzi/root": "gaanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "magaanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "maganga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuyaga uhuha uva ku ijwi ugana mu Rwanda","Vent soufflant de l’île Ijwi vers le Rwanda.","Wind blowing from Ijwi Island towards Rwanda."
            ]
    },
    "rugango": {
        "umuzi/root": "gáango",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugáango",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugango",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ufite imbaraga nyinshi","Personne de grande vigueur", "Person of great vigor"
            ]
        },
    "ruganirwa": {
        "umuzi/root": "gaaniirwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruggaaniirwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruganirwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "icyamamare","personne célèbre","celebrity"
            ]
    },
    "kagano": {
        "umuzi/root": "gano",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kagano",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kagano",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burengerazuba bwa ruguru bwa perefegitura ya Cyangugu","Colline de nord-est de la prefecture Cyangugu","Hill located in noth east of Cyangugu prefecture"
            ]
    },
    "ruganwa": {
        "umuzi/root": "ganwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruganwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruganwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igishanga kiri hagati ya Mburabuturo na Kiyovu na Kimihurura muri perefegitura y'umugi wa Kigali","marais situé entre Kiyovu,Mburabuturo et Kimihurura ","wetlands located between Kiyovu,Mburabuturo and Kimihurura in Kigali","NONE"
            
            ]
        
    },
    "biganza": {
        "umuzi/root": "gaanza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bigaanza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "biganza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
               "umuntu ugira ibambe" ," Personne généreuse","generous person"
            ]
    },
    "muganza": {
        "umuzi/root": "gaánza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muggaánza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muganza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burasirazuba bw'amajyepfo bwa perefegitura ya Butare wahaye izina komini uri mo","Colline et commune situées dans le sud", "Hill and municipality located in the south"
            ]
    },
    "ruganzu": {
        "umuzi/root": "gaánzu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruggaánzu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruganzu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'ubwami ryigeze gufatwa n'abami babiri Bwimba na Ndori","Nom dynastique porté par deux rois Bwimba et Ndori.", "Dynastic name held by two kings, Bwimba and Ndori."
            ]
    },
    "mugara": {
        "umuzi/root": "gaara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muggaara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina abahigi bita intare","surnom attribué au lion","Lion nickname"
            ]
    },
    
    "rugaragaza": {
        "umuzi/root": "garagaza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugaragaza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugaragaza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "inzara yateye ahayinga 1940-1945","Famine des années 1940-1945","hunger that strunk in 1940-1945"
            ]   
    },
    "kigarama": {
        "umuzi/root": "garama",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kigarama",
            "mu bwinshi/plural": "NA"

         }, "bandika/writing": "kigarama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Umusozi wo mu majyepfo y'iburasirazuba bwa perefegitura ya Kibungo","Colline et commune située dans la prefecture Kibungo","Municipality and hill located in Kibugno prefecture"
            ]
    },
    "bugarama": {
        "umuzi/root": "garama",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bugarama",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bugarama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina rya komini iherereye muri ako karere","Commune située dans cette même région de Bugarama", "Municipality located in this same region of Bugarama"
            ]
            
    },
    "magaramake": {
        "umuzi/root": "maké",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "magaramaké",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "magaramake",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu ukunda kurwaragurika","Surnom d’une pers maladive","Nickname of a sickly person."
            ]
   
    },
    "magarayagacuma": {
        "umuzi/root": "ágacumá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mágaráyágacumá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "magarayagacuma",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu ukunda inzoga cyane ku buryo atayisiba","Surnom de celui qui prend la bière quotidiennement.", "Nickname for someone who drinks beer daily."
            ]
    },
    
    "mugasa": {
        "umuzi/root": "gasa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugasa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugasa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwe mu bagaragu ba Ryangombe wambutsaga","Serviteur de Ryangombe qui est chargé de faire passer les cours d’eau.","Servant of Ryangombe responsible for guiding the waterways."
            ]
    },
    "kigasari": {
        "umuzi/root": "gasaari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kigasaari",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kigasari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igisi kiri hagati ya za komini Runyinya na Maraba muri perefegitura ya Butare","Mont situé entre les communes actuelles de Runyinya et Maraba dans la préfecture de Butare.", "Mountain located between the current municipalities of Runyinya and Maraba in the Butare prefecture."
            ]
    },
    
    "rugata": {
        "umuzi/root": "gáta",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugáta",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugata",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imvura nyinshi kandi yakwiriye ahantu hose","Pluie forte et qui couvre un grand territoire.", "Heavy rain that covers a large area."
            ]
    },
    "bugata": {
        "umuzi/root": "gáta",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bugáta",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bugata",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ibara ryo mu bibohwa","Dessin de vannerie", "Drawing of weaving"
        ]
    },
    "rugayantete": {
        "umuzi/root": "gayanteete",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugayanteete",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugayantete",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'amasaka yera kandi manini","Variété de sorgho à gros épis blancs.","Variety of sorghum"
            ]
    },
    "ingegera": {
        "umuzi/root": "gegera",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bugegera",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bugegera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "inzererezi","vagabond","vagabond"
            ]
    },
    "rugema": {
        "umuzi/root": "gema",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugema",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugema",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ingabo idahusha mu cyico","Guerrier qui ne rate jamais", "Warrior who never misses the opponent"
            ]
    },
    "kigembe": {
        "umuzi/root": "geembe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kigeembe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kigembe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini yawitiriwe iri ku mupaka mu majyepfo ya perefegitura ya Butare ikaba ikikijwe n'akanyaru na za komini Nyakizu Gishamvu Nyaruhengeri na Kibayi", "Nom d’une colline et d’une commune situées à la frontière du pays dans l’extrême sud de la préfecture de Butare"
            ]
    },
    "kagembegembe": {
        "umuzi/root": "géembegéembe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kagéembegéembe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kagembegembe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'inzara yigeze gutera ku ngoma ya Rwabugiri imvura yarangije amasaka abantu bakarya ibigembegembe","Nom d’une famine qui a sévi sous le règne de Rwabugiri et pendant laquelle les gens se nourrissaient de l’herbe parce que la pluie avait détruit la récolte de sorgho.","Name of a famine that occurred during the reign of Rwabugiri, during which people fed on the herb Sonchus because the rain had destroyed the sorghum harvest."
            ]
    },
    "kageme": {
        "umuzi/root": "geme",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kageme",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kageme",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ikimera kivura mburugu","Espèce de plante médicinale utilisée pour soigner la syphilis.","Species of medicinal plant used to treat syphilis."
            ]
    },
    "kigeme": {
        "umuzi/root": "gemé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kigemé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kigeme",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'musozi wo muri komini Nyamagabe muri perefegitura ya Gikongoro hubatswe paruwasi y'abaporositanti.","colline de la commune nyamagabe, Gikongoro prefecture","Hill located in Nyamagabe municipality"
            ]
    },
    "ngenda": {
        "umuzi/root": "geenda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ngeenda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ngenda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu Bugesera perefegitura ya Kigali wahaye izina komini uri mo","Colline et commune de la région de l’Ubugesera dans la préfecture de Kigali.","Hill in Bugesera, Kigali prefecture"
            ]
        
    },
    "rugenderwa": {
        "umuzi/root": "geendérwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugeendérwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugenderwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umupfumu cg umuvuzi w 'ikimenyabose","Devin guérisseur réputé","Renowned diviner and healer"
            ]
    },
    "rugendo": {
        "umuzi/root": "geendo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugendo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugendo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzu yugarije kambere mu bwami","Maison de la cour royale qui en importance vient au second rang après","House of the royal court that ranks second in importance"
            ]
    },
    "magendu": {
        "umuzi/root": "geéndu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "maggeéndu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "magendu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ku buryo bufifitse butemewe n'amategeko", "D’une façon illicite", "illicit, and clandestine manner"
            ]
    },
    "mugengeri": {
        "umuzi/root": "géengeéri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugéengeéri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugengeri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igisheshe cy'igihitira kigenewe gucanwa", "Bouse sèche vieille de plusieurs années et destinée à faire du feu.","Dry dung several years old, intended for use as fuel."
            ]
    },
    
    "umugenurano": {
        "umuzi/root": "génuurano",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umugénuurano",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umugenurano",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ingingo ishingiye ku ikintu iki n'iki","Dont le nom est significatif","Whose name is significant"
            ]
 
    },
    "mugera": {
        "umuzi/root": "gera",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugera",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Gafunzo", "Colline de la commune de Gafunzo.","Hill of the municipality of Gafunzo."
            ]
    
   
    },
    "rugerero": {
        "umuzi/root": "gereero",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugereero",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugerero",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'umusozi uri muri komini Rubavu ho muri perefegitura ya Gisenyi","Nom d’une colline de la commune Rubavu dans la préfecture de Gisenyi.","Name of a hill in the municipality of Rubavu in the Gisenyi prefecture."
            ]
    },
    "kigeri": {
        "umuzi/root": "geri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kigeri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kigeri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Rimwe mu mazina y'ubwami bw'ingoma nyiginya umwami wabaga yimanye iryo zina akaba yaragombaga kubyutsa intambara kugira ngo yagure igihugu","Un des noms dynastiques des rois Nyiginya.","One of the dynastic names of the Nyiginya kings."
            ]
    },
    "rugero": {
        "umuzi/root": "gero",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugero",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugero",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu munini kandi wuujurije","Surnom d’une pers grande et grosse.","nickname of a tall and fat person"
            ]
    },
    
    "rugesanzugi": {
        "umuzi/root": "gesanzuugi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugesanzuugi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugesanzugi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba impyisi","Surnom de l’hyène","Nickname of the hyena"
            ]
    
    },
    "mugeti": {
        "umuzi/root": "géti",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugéti",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugeti",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu cyangiritse cyane","Chose abîmée.","Something damaged."
            ]
    },
    "rugeyo": {
        "umuzi/root": "geyo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugeyo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugeyo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba impfizi y'intaama","Surnom du bélier","Nickname of the ram"
            ]
   
    },
    "mutanyobwa": {
        "umuzi/root": "utányoobwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muutanyobwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mutanyobwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu udashobokera abandi","Surnom donné à une personne insociable","Nickname given to an unsociable"
            ]
    
   
    },
    "mugiga": {
        "umuzi/root": "giga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugiga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugiga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara ifata mu bwonko mu bikanu no mu rutirigongo ibimenyetso byayo bikamera nk'ibya tifusi","Méningite cérébro","Cerebrospinal meningitis."
            ]
    },
    "mugina": {
        "umuzi/root": "gina",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugina",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugina",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi na komini biri mu burasirazuba bwa perefegitura ya Gitarama","Colline et commune situées dans l’est de la préfecture de Gitarama.","Hill and municipality located in the eastern part of Gitarama Prefecture."
            ]
    },
    "migina": {
        "umuzi/root": "gina",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "migina",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "migina",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugezi wisuka mu Kanyaru muri komine ya Kigembe perefegitura ya Butare", "Rivière qui se jette dans l’Akanyaru dans la commune de Kigembe (préfecture de Butare).","River that flows into the Akanyaru in the municipality of Kigembe (Butare Prefecture)."
            ]
    },
    "rugina": {
        "umuzi/root": "gina",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugina",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugina",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikimasa gifite ibara ry'urugina", "Boeuf ou taureau à robe brun clair.","Light brown cow or bull."
            ]
   
    },
    "magingo": {
        "umuzi/root": "giingo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "magiingo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "magingo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igihe iki n'iki",  "Moment donné de la journée ou de la nuit.","Given moment of the day or night."
            ]
    },
    
    "rugira": {
        "umuzi/root": "girá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugirá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bitira imana", "Nom donné à Dieux","Name given to God"
            ] 
    },
    "kagoma": {
        "umuzi/root": "goma",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kagoma",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kagoma",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw igisiga kinini cyane cyo mu ubwoko bw'ibitungwa n'inyama gusa","aigle","eagle"
            ]
    },
    "kigombe": {
        "umuzi/root": "goombe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kigoombe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kigombe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akagezi kambukiranya umugi wa Ruhengeri", "Ruisseau qui traverse la ville de Ruhengeri.","Stream that runs through the city of Ruhengeri."
            ]
    },
    "rugombera": {
        "umuzi/root": "goombéra",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruggoombéra",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugombera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akavugirizo k'abahigi barengurana bategeranye","Sifflement émis par la bouche des chasseurs qui communiquent à distance pour s’orienter mutuellement.","Whistling emitted by hunters to communicate between themselves"
            ]
    },
    "ngombwa": {
        "umuzi/root": "goombwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ngoombwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ngombwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu cg igikorwa icyo ari cyo cyose by'ingirakamaro","important","important"
            ]
    
    },
    "ubugome": {
        "umuzi/root": "gomé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubugomé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubugome",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubugizi bwa nabi","Méchancete","cruelty"
            ]
    },
    "rugomwa": {
        "umuzi/root": "gomwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugomwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugomwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umurwanyi utagira ibambe","Guerrier cruel impitoyable","Brutal, merciless warrior."
            ]
    },
    "rugona": {
        "umuzi/root": "goná",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugoná",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugona",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umutsi utwara amaraso ugaterera ahagana mu rwano","Artère sous-clavière","Subclavian artery"
            ]
    },
    "rugongo": {
        "umuzi/root": "goongo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugoongo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugongo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akabiri gashyukwa kaba mu rwasa rw'igituba hejuru","Clitoris","Clitoris"
            ]
    },
    "mutembo": {
        "umuzi/root": "teémbo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muteémbo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mutembo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzu ifite igisenge cy' impande ebyiri", "Maison dont le toit a deux pans","House with a gabled roof"
            ]
    },
    "bugonya": {
        "umuzi/root": "goonyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bugoonyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bugonya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita agasaho k'impindura","Vésicule de la caillette.","Vesicle of the ruminant stomach"
            ]
   
    },
    "kagoro": {
        "umuzi/root": "goro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kagoro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kagoro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwe mu bahungu ba Ryangombe", "L’un des fils de Ryangombe","L'un des fils de Ryangombe"
            ]
   
    },
    "ngororero": {
        "umuzi/root": "gororero",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ngororero",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ngororero",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Satinsyi wahaye izina superefegitura uri mo iyo superefegitura igizwe n'amakomini Satinsyi Kibirira na Ramba.","NONE","NONE"
        ]
    },
     "muzo": {
        "umuzi/root": "zo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muzo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muzo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " izina bahimba igikumwe", "Surnom du pouce","another name for thumb"
            ]
    },
    "maguge": {
        "umuzi/root": "gugé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "magugé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "maguge",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'akaguge gato","singe","monkey"
            ]
    },
    "mugugu": {
        "umuzi/root": "gugu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugugu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugugu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubutaka bwenda kumera nk'umukungugu buseseka cyane ntiburumbuke","Sol très friable et stérile","Very loose and sterile soil"
            ]
    },
    "ruguma": {
        "umuzi/root": "guma",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruguma",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruguma",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'amasaka","Variété de sorgho.","Variety of sorghum."
        ]
    },
    
    "ngunda": {
        "umuzi/root": "guunda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ngunda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ngunda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu wo mu migani bavuga ko yari igihangange mu kurya no mu kunywa ariko kandi no mu kubasha imirimo","Géant légendaire qui était réputé grand mangeur et grand buveur mais aussi grand travailleur.","Giant legend known for being a great eater and drinker, but also a hard worker."
            ]
    },
    "rugundirakirago": {
        "umuzi/root": "guundiirakirago",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruguundiirakirago",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugundirakirago",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bita umuntu wanegekajwe n'ubusaza cg indwara cg ubunebwe akaryamira ","Surnom d’une personne affaiblie par la vieillesse et la maladie ou d’un paresseux.","nickname for a lazy person"
            ]
    
    },
      "bugurububiri": {
        "umuzi/root": "bubiri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bugurububiri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bugurububiri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ijambo rijimije rivuga umuntu","Mot voilé désignant la pers humaine.","veiled word designating human person."
            ]
    },
    
    "mugurumizi": {
        "umuzi/root": "gurumizi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugurumizi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugurumizi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuriro w'indwara mwinshi cyane","Forte fièvre","strong fever"
            
            ]
    },
    "mugusa": {
        "umuzi/root": "gusá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mugusá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mugusa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burasirazuba bwa perefegitura ya Butare","Colline et commune situées dans l’Est de la préfecture de Butare.", "Hill and municipality located in the East of the Butare prefecture."
            
        ]
   
    },
    
    "rugwe": {
        "umuzi/root": "gwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rugwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rugwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami wa cumi n'icyenda w'urwanda ushingiye ku bucurabwenge ukabara usubira inyuma","Dix-neuvième roi du Rwanda selon la généalogie officielle en comptant à reculons","Nineteenth king of Rwanda according to the official genealogy counting backward"
            
            ]  
    },
    "muha": {
        "umuzi/root": "ha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugezi uri mu Burundi hafi y'ibujumbura","Rivière du Burundi près de Bujumbura.","River of Burundi near Bujumbura."
            ]
    
    },
    "muhabura": {
        "umuzi/root": "habuura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muhabuura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muhabura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikirunga gihera ibindi mu burasirazuba kiri ku rubibi rw'urwanda na Uganda", "Nom propre du volcan rwandais situé le plus au nord à la frontière de l’Ouganda.","Proper name of the Rwandan volcano located furthest north at the border of Uganda."
            ]
   
    
    },
    "impagarara": {
        "umuzi/root": "hágarará",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "impágarará",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "impagarara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ibintu by'ibizira byaduka ku muntu cg mu abantu benshi bigatuma babura amahoro","troubles", "difficulties"
            ]
    
    },
    "impage": {
        "umuzi/root": "haáge",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "impage",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu umerewe neza kubera kuba adashonje", "Personne qui se sent bien parce qu’elle est repue.","Person who feels good because she is full."
            ]
   
    },
    
    "ruhaha": {
        "umuzi/root": "hahá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhaha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhaha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igikorora kiremereye gihora ho kandi cyivugiza mu gituza iyo umuntu akoroye","Grosse toux permanente qui retentit dans la poitrine","Severe persistent cough that resonates in the chest"
            ]
    },
    "gahaha": {
        "umuzi/root": "hahá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahahá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahaha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara yo gukorora irwarwa n'imbwa","Toux des chiens","Kennel cough"
            ]
    },
    "muhahano": {
        "umuzi/root": "haahano",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muhaahano",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muhahano",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu umuntu yihahiye adakomora kuri ba se na ba sekuru","Ce qu’on s’est procuré soi", "What one has obtained for oneself" 
            ]
    },
    "ubuhahara": {
        "umuzi/root": "hahára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buhahára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buhahara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubugugu","avarice","greed" 
            ]
    },
    "ruhahira": {
        "umuzi/root": "haahira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhaahira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhahira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu w'umuryi wa cyane cg w'igisambo kandi akagira amabondo agaragara", "Surnom donné à un grand mangeur ou à un gourmand ventru.","Nickname given to a big eater or a bloated foodie"
            ]
    },
    "impaka": {
        "umuzi/root": "haká",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "impaká",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "impaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuvugana kudahuje ibitekerezo umwe ashaka kwemeza undi", "Discussion controversés.","controversies" 
            ]
    
    },
    "mahama": {
        "umuzi/root": "haáma",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mahaáma",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mahama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Izina bita impyisi kubera ko igira ibakwe mu gucukura no gusenya amazu ishaka ibitungwa","Surnom donné à l’hyène","Nickname given to the hyena"
            ]
    },
    "ruhamanya": {
        "umuzi/root": "hamánya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhamánya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhamnya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu uzi kuboneza cg uhamya rimwe agahita agusha","Surnom donné à qqn qui vise bien ou qui tue du premier coup.", "Nickname given to someone who aims well or who kills with the first shot."
            ]
    },
    "buhambe": {
        "umuzi/root": "haambé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buhaambé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buhambe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Umusozi wo muri komini Kibari mu majyepfo gato y'umurwa wa perefegitura ya Byumba","Colline de commune Kibari tout près de la prefecture Byumba","Hill in Kibari municipality, byumba prefecture"
            ]
   
    },
    "impambiro": {
        "umuzi/root": "háambiiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "impáambiiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "impambiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Uburyo akoresha ahambira","Manière de lier", "Way of tying" 
            ]
   
   
    },
    "gihamya": {
        "umuzi/root": "hamyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gihamyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gihamya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikimenyetso gishobora kwemeza abo ubwira ko ibyo uvuga cg ukora ari ukuri","Preuve","piece of evidence"
            ]
    },
    "ruhamya": {
        "umuzi/root": "hamyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhamyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhamya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ijambo cg agatsiko k'amagaambo kavuga imico cg imimerere y'irindi gasobanura","Attribut d’un mot", "Attribute of a word"
            ]
   
    },
    "agahandagaza": {
        "umuzi/root": "haándagaza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agahaándagaza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahandagaza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzira nyabagendwa","Chemin public","Public way" 
                
            ]
    },
    "mpandura": {
        "umuzi/root": "haanduurá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mpaanduurá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mpandura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Ubwoko bw'akanyabwoya kaba hasi kagatungwa n'utubabi tw'ibiti kakagira amabara yirabura n'ay'umweru byatinda kakazahinduka ikinyugunyugu", "Espèce de chenille", "A type of hairy caterpillar"
            ]
    },
    "mpanga": {
        "umuzi/root": "haanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mpaanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mpanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Ikiyaga kiri mu burasirazuba bwo hagati bwa perefegitura ya Kibungo","Lac situé dans l'est de la prefecture Kibungo","A type of hairy caterpillar that defoliates, belonging to the family Nymphalidae."
            ]
    },
    "bihanga": {
        "umuzi/root": "haanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bihaanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bihanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bita umuntu wakutse amenyo","Surnom donné à une personne qui a perdu plusieurs dents","Nickname given to a person who has lost several teeth"
            ]
    
    },
    "gihanga": {
        "umuzi/root": "háanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "giháanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gihanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami w'urwanda bavuga mu bwiru ariko akaba atazwi mu mateka", "Roi du Rwanda mentionné par la généalogie officielle qui lui attribue de multiples innovations mais inconnu de l’histoire","King of Rwanda mentioned in the official genealogy"
            ]
    },
    "ruhanga": {
        "umuzi/root": "háanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhháanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwe mu bahungu ba Ryangombe","Un des fils de Ryangombe.", "One of the sons of Ryangombe."
            ]
    },
    "gahanga": {
        "umuzi/root": "haánga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahhaánga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burengerazuba bw'amajyepfo bwaa komini Kanombe","Colline située dans la partie sud", "Hill located in the southern part."
            ]
  
    },
     "gakabi": {
        "umuzi/root": "kábi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gakábi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gakabi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bita umuntu upfusha uwo bashakanye n'undi agiye yishumbusha wese agapfa", "Surnom qu’on donne à une personne qui survit à plusieurs conjoints successifs.", "Nickname given to a person who survives several successive spouses."
            ]
    
   
    },
    "ruhango": {
        "umuzi/root": "haango",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhaango",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhango",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini ya Tambwe wahaye izina superefegitura uri mo","colline de la commune Tambwe","Hill located in Tambwe municipality"
            ]
   },
    "buhanya": {
        "umuzi/root": "hánya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buhánya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buhanya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ku buryo buhanitse butangaje","D’une manière inconcevable", "In an unimaginable way"
            ]
   
    },
    
    "ruharamba": {
        "umuzi/root": "háraambá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruháraambá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruharamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ikimera","Espèce de plantenon identifiée","Species of plant identified"
            ]
    },
    "agahararo": {
        "umuzi/root": "hararo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agahararo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahararo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Urukundo umuntu agirira uwo bakimenyana","Amour de la nouveauté passion du neuf","Love of novelty"
            ]
 
    },
    "agaharuruko": {
        "umuzi/root": "haruruko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agaharuruko",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agaharuruko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuba umuntu yumva atagikunze umuntu cg ikintu yahoze akunda","Tendance à cesser d’aimer qqn ou qqch à un moment donné","Tendency to stop loving someone or something at a given moment"
            ]
    },
    "imiharuzo": {
        "umuzi/root": "háruzo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imiháruzo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imiharuzo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "inyikirizo y'indirimbo isingiza inka iyi n'iyi","Refrain d’un poème pastoral.", "Refrain in a pastoral poem"
            ]
    
    },
    "ruharwa": {
        "umuzi/root": "harwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruharwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruharwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugore utabyara","Femme stérile", "Sterile woman"
            ]
    },
    "ruhashya": {
        "umuzi/root": "hashyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhashyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhashya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi na komini biri muri perefegitura ya Butare ahagana mu majyaruguru uri muri komini wahaye izina","Colline de la préfecture de Butare vers le nord.","Hill of the prefecture of Butare towards the north."
            ]
    },
    "muhashyi": {
        "umuzi/root": "haashyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muhaashyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muhashyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umukozi wa leta ushinzwe kugenzura imigendere y'ibyuma mu mihanda","Fonctionnaire de l’Etat qui contrôle la circulation des véhicules", "State official who controls vehicle traffic"
            ]
    },
    "agahato": {
        "umuzi/root": "hato",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agahato",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahato",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ugukoresha umuntu ikintu adashaka", "Contrainte violence", "Constraint violence"
            ]
    },
    "ruhaya": {
        "umuzi/root": "hayá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhayá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhaya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bita umugabo ukunda gusambana", "Surnom d’un débauché", "Nickname of a debauchee"
            ]
   
    },
    "muhazi": {
        "umuzi/root": "házi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muházi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muhazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikiyaga cyo mu burasirazuba bw'urwanda hagati ya perefegitura za Kigali na Byumba na Kibungo","Lac de l’est du Rwanda situé entre les préfectures de Kigali de Byumba et de Kibungo.","Lake in eastern Rwanda located between the prefectures of Kigali, Byumba, and Kibungo."
                
                ]
    },
    "agahazo": {
        "umuzi/root": "hazo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahazo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imyifatire mibi mu mico y'umukobwa wagumiwe akiyandarika","Inconduite d’une fille","Misconduct of a girl"
            ]
    
    },
    "ruhebeba": {
        "umuzi/root": "hebéba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhebéba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhebeba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inkaka y'ihene", "Pénis de bouc","Goat's penis"
            ]
      
   
    },
    "agahebuzo": {
        "umuzi/root": "hébuuzo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agahébuuzo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahebuzo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akarusho ikintu gihatse ibindi gifite", "extraordinaire.", "unparalleled"
            ]
    },
    "impehe": {
        "umuzi/root": "heehe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "impeehe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "impehe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Abantu cg inyamaswa byabuze umugenga", "Pers ou animaux sans chef", "People or animals without a leader"
            ]
    },
    "muheka": {
        "umuzi/root": "heeka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muheeka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muheka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'igihaza kinini","Espèce de grosse courge","Species of large pumpkin"
            ]
    
    
    },
    "ihekenya": {
        "umuzi/root": "hékenyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imhékenyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ihekenya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibintu umuntu ariye ahekenya", "Aliments mangés crus", "Foods eaten raw"
            ]
    },
    "muhekenyi": {
        "umuzi/root": "hékenyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muhékenyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muhekenyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara irwarwa mu ngingo hakaribwa","Rhumatisme articulaire", "Joint rheumatism"
            ]
    },
    "ruhekerababyeyi": {
        "umuzi/root": "héekerabábyeeyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhéekerabábyeeyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhekerababyeyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu w'umunyampuhwe nyinshi","Nom donné à une pers très compatissante.","Name given to a very compassionate person."
            ]
    },
    "biheko": {
        "umuzi/root": "heeko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "biheeko",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "biheko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imana itanga urubyaro", "dieu mythique la fécondité","mythical god of fertility"
            ]
    },
    "ruhekurirababyeyi": {
        "umuzi/root": "héekuurirabábyeeyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhéekuurirabábyeeyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhekurirababyeyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'umugome kandi w'umwicanyi","Personne méchante et meurtrière assassin.", "A murderous person"
            ]
    },
    "bahema": {
        "umuzi/root": "hemá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bahema",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'agasimba","Espèce de chenille.", "Species of caterpillar."
            ]
   
    
    },
    "agahembura": {
        "umuzi/root": "heémbuura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agaheémbuura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahembura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu umuntu arya cg anywa akumva ahembutse", "Nourriture ou boisson qu’on prend quand on en a grand besoin.","Food or drink that one takes when in great need."
            ]
    
    },
    "gahenda": {
        "umuzi/root": "héenda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahéenda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahenda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umunyiginya ukomokwa ho n'umuryango wamwitiriwe","Personnage du clan Nyiginya ancêtre éponyme d’un lignage.","Character of the Nyiginya clan, eponymous ancestor of a lineage."
            ]
    },
    "imihenda": {
        "umuzi/root": "héenda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imihéenda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imihenda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inka cg abantu benshi", "Foule multitude grand troupeau.","Crowd, large herd."
            ]
    
    },
    "bihendo": {
        "umuzi/root": "héendo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bihéendo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bihendo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umugabo ufite abagore benshi","Surnom du polygame", "Nickname of the polygamist"
            ]
   
    },
    "mahenga": {
        "umuzi/root": "heenga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "maheenga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mahenga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu ugenda umubyimba we uhengamye","Surnom qu’on donne à une pers qui se tient penchée d’un côté.", "Nickname given to a person who leans to one side."
            ]
    },
    "ruhengeri": {
        "umuzi/root": "heengeri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruheengeri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhengeri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Kigombe wubatse ho umurwa wa perefegitura yitwa iryo zina","Colline de la commune de Kigombe sur laquelle se trouve le chef", "Hill in the Kigombe commune where the chief resides."
            ]
    },
    "gahengeri": {
        "umuzi/root": "heengeri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gaheengeri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahengeri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Murambi perefegitura ya Byumba", "Colline de la commune de Murambi.", "Hill in the commune of Murambi."
            ]
    
    },
    "gahenya": {
        "umuzi/root": "heenyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gaheenyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahenya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara y'amaso itukuza igice cyose cy'umweru cyo mu jisho cg uruhande rumwe rwacyo","Kératite maladie qui fait rougir le blanc de l’oeil ptérygion.","a disease that causes redness of the white of the eye"
            ]
    
   
    },
    "imperuka": {
        "umuzi/root": "héruuká",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "impéruuká",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imperuka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umunsi abemera bavuga ko isi izaraangiriraho","fin des temps","last coming"
            ]
   },
    "aheze": {
        "umuzi/root": "héze",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "aheze",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akantu k'ubusabusa kadahagije katagize icyo kamara kagayitse mu jisho","Chose minuscule et insuffisante sans valeur.", "Minuscule thing,insufficient of no value"
            ]
    },
    "gahiga": {
        "umuzi/root": "higa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahiga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahiga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'inzoka yo mu Kinyaga","Serpent de l’Ikinyaga","Snake of the Ikinyaga"
            ]
   
    },
    "muhima": {
        "umuzi/root": "himá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "muhimá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "muhima",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imandwa ibandwa n'abatutsi","Esprit du culte de Ryangombe qui est invoqué par les Tutsi", "Spirit of the Ryangombe cult that is invoked by the Tutsi"
            ]
    },
    "gahima": {
        "umuzi/root": "himá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahima",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahima",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'inzoka y'agasozi","Serpent non identifié", "Unidentified snake"
            ]
    },
    "gahimakazi": {
        "umuzi/root": "himákazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahimákazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahimakazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ubwoko bw'umukenke","Herbe de la famille des Poacées Hyparrhenia", "Grass of the Poaceae family"
            ]
   
    },
    "igihimbano": {
        "umuzi/root": "hiimbano",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "igihiimbano",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "igihimbano",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Kivumbuwe ariko kitari gisanzwe","Inventé fictif", "Invented fictional"
            ]
 
    },
    "ruhimbazabasazi": {
        "umuzi/root": "hiimbaazabasazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhiimbaazabasazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhimbazabasazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'umwenda wirabura uboshye nka kaki","Espèce de tissu noir de la même texture que le kaki.", "Species of black fabric of the same texture as khaki"
            ]
    },
    "buhinda": {
        "umuzi/root": "hiinda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buhiinda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buhinda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'insina cg igitoki yera", "Variété de bananier ou régime de bananes qu’il produit.", "Variety of banana plant or bunch of bananas that it produces."
            ]
    },
    "gihindamuyaga": {
        "umuzi/root": "hiindamuyaga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gihiindamuyaga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gihindamuyaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burengerazuba bwa komini ya Mbazi Perefegitura ya Butare utuwe ho n'abapadiri b'ababenedigitini","Colline située à l’ouest dans la commune Mbazi.", "Hill located to the west in the municipality of Mbazi."
            ]
    },
    "gahindiro": {
        "umuzi/root": "hiindiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahiindiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahindiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami wa gatandatu w'urwanda ushingiye ku bucurabwenge ukabara usubira inyuma, izina ry'umwami yuhi","Sixième roi du Rwanda selon la généalogie officielle en comptant à reculons","Sixth king of Rwanda according to the official genealogy when counted backward"
            ]
   
    },
    "buhindo": {
        "umuzi/root": "hiindo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buhiindo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buhindo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'insina","Variété de bananier", "Variety of banana plant"
            ]
  
    },
    "mihinga": {
        "umuzi/root": "hiinga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mihiinga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mihinga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri Komini Rusumo Perefegitura Kibungo","Colline de la commune de Rusumo", "Hill in the municipality of Rusumo"
            ]
    },
    "ruhingika": {
        "umuzi/root": "hiingika",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhiingika",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhingika",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inka ifite amahembe yerekeye ku mpande","Vache dont les cornes sont dirigées sur les côtés","Cow whose horns are directed to the sides"
            ]
   
    },
    "mihingwe": {
        "umuzi/root": "hiingwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mihiingwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mihingwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'uruyuki ruba mu muzinga ntirutare kandi ntiruryane","Faux bourdon mâle de l’abeille.", "Male drone bee."
            ]
    
    },
    "mihiri": {
        "umuzi/root": "hiri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mihiri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mihiri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu utagira umurasanira", "Personne qui n’a pas de défenseurs", "Person who has no defenders"
            ]
   
    },
    "imihiringisi": {
        "umuzi/root": "hiriingisi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imihiriingis",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imhiringisi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubushyuhe bukabije cyane buterwa n'uko ibintu byegeranye cyane bukabitera kwangirika","chaleur produite par des objets qui se chevauchent","heat produced by overlapping objects"
            ]
    },
    "imihirita": {
        "umuzi/root": "hiriita",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imihiriita",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imihirita",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
             "Umwete uri mo agakabyo","zèle excessif.","excessive zeal"
            ]
    },
    "mihiro": {
        "umuzi/root": "hiro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mihiro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mihiro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'inzoka yo mu migani","Espèce de serpent légendaire.", "Species of legendary serpent."
            ]
   
    },
    "ruhiryi": {
        "umuzi/root": "hiryi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhiryi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhiryi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amarwa abishye kandi adahiye","Bière de sorgho de mauvais goût insuffisamment fermentée.", "Bad-tasting sorghum beer that is insufficiently fermented."
            ]
    },
    "ruhishyi": {
        "umuzi/root": "hishyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhishyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhishyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu w'intekezi uhorana inda yujurije","Surnom d’un grand mangeur ventru.","Nickname pot-bellied eater"
            ]
   
  
    },
    "bihobe": {
        "umuzi/root": "hobe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bihobe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bihobe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu wanobotse mo amaso", "Personne qui a les yeux crevés","Person who has hollow eyes."
            ]
    },
    "buhobero": {
        "umuzi/root": "hoobero",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buhoobero",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buhobero",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'ibihaza","Variété de courge","Variety of squash"
            ]
   
    },
    "gahoga": {
        "umuzi/root": "hoogá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahoogá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahoga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwana ukunda kurizwa n'ubusa","Enfant pleurnichard","Whiny child"
            ]
    
    },
    "imihomamunwa": {
        "umuzi/root": "homamunwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imihomamunwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imihomamunwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Induru ivuga ubutaretsa","Cri d’alarme prolongé", "Prolonged alarm cry"
            ]
    },
    "agahomamunwa": {
        "umuzi/root": "homamunwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agahomamunwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahomamunwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu gitangaaje ku buryo budasubirwa ho","Chose ahurissante", "Astonishing thing" 
            ]
    },
    "gihome": {
        "umuzi/root": "homé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gihomé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gihome",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubushita cg ibihara bipfukiriye umubiri wose","Variole ou varicelle dont l’éruption couvre le corps.","Smallpox or chickenpox whose rash covers the body" 
            ]
   
    },
    "ruhondo": {
        "umuzi/root": "hoondo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhoondo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhondo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikiyaga kiri mu majyaruguru y'uburasirazuba bwa perefegitura ya Ruhengeri","Lac situé dans la partie nord", "Lake located in the northern part"
            ]
    },
    "igihongo": {
        "umuzi/root": "hoongo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "igihoongo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "igihongo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara y'uburo ibwumisha butarera","Maladie qui dessèche les épis d’éleusine avant la maturité.","Disease that dries out the sorghum ears before maturity"
            ]
    },
    "gahongo": {
        "umuzi/root": "hoongo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahoongo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahongo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'indwara y'itabi","Espèce de maladie du tabac.", "Type of tobacco disease" 
            ]
    },
    "ruhonyora": {
        "umuzi/root": "honyoora",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhonyoora",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhonyora",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu ufite ibirenge bitambamye","Surnom d’une pers qui a les pieds bots", "Nickname of a person who has clubfoot" 
            ]
    },
    "ruhorahoza": {
        "umuzi/root": "horahoza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhorahoza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhorahoza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Umwishi udahusha","Grand tueur", "Great killer"
                
            ]
    },
    "buhubane": {
        "umuzi/root": "hubáne",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "buhubáne",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "buhubane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bitirira umuntu ufite iminwa n'amatama byahubanye biturutse ku gukuka amenyo","Surnom d’une pers qui a les joues creuses parce qu’elle a perdu les dents.","Nickname of a person who has hollow cheeks because they have lost their teeth"
            ]
    },
    "ruhubanya": {
        "umuzi/root": "hubánya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhubánya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhubanya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bitirira umuntu w'umunyenda","Surnom du gourmand","Nickname of the glutton"
            ]
   
    },
    "agahubuzo": {
        "umuzi/root": "hubuzo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agahubuzo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahubuzo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ugukora ikintu mu kanya k'ubusa ugicishije ku murimo wundi utinda wakoraga", "Abandon d’un travail qui exige beaucoup de temps en vue de régler une affaire rapide.","Abandonment of a time-consuming task in order to settle a quick matter" 
            ]
    },
    "agahuge": {
        "umuzi/root": "hugé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agahugé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agahuge",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akamenyero gatuma umuntu akora ikintu atabanje gutekereza", "Habitude acquise accoutumance.", "Acquired habit" 
            ]
    },
    "huhuguza": {
        "umuzi/root": "hugu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "guhuguza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "guhuguza",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Ukunyaga umuntu ibintu bye ukabitwara ubyita ibyawe", "Fait de s’approprier les biens d’autrui par tricherie","ct of taking possession of others' property through cheating"
            ]
    },
    "ruhugura": {
        "umuzi/root": "huguura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhuguura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhugura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuti bahadika inka bayitsindira","Produit qu’on introduit dans la vulve d’une vache pour l’habituer à un veau qui n’est pas le sien.","A product introduced into the vulva of a cow to accustom her to a calf that is not her own" 
            ]
    },
    "mpuhugutu": {
        "umuzi/root": "hugutu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mpuhugutu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mpuhugutu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "izina bahimba umuntu ufite amatama manini", "Surnom d’une pers joufflue.", "Nickname of a chubby person" 
               ]
    },
    "guhuha": {
        "umuzi/root": "huuha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "guhuuha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "guhuha",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "Koohereza umwuka ku umuntu cg ku ikintu uwukuye mu kanwa" ,"Souffler","blow"
            ]
    },
    "gihuha": {
        "umuzi/root": "huuha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gihuuha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gihuha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu waheranije mu kubeshya","Surnom du grand menteur","Nickname of the great liar"
            ]
   
    },
    "ruhuhezi": {
        "umuzi/root": "huheézi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhuheézi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhuhezi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Izina bahimba impyisi kuko imira bunguri","Surnom donné à l’hyène parce qu’elle avale sans mâcher.","Nickname given to the hyena because it swallows without chewing"
            ]
    },
    "impuhwe": {
        "umuzi/root": "huhwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imphuhwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imphuhwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu cyenda kumera nk'agahinda umuntu yiyumva ku mutima agitewe no kubona undi ari mu byago","Compassion", "Compassion"
            ]
   
    },
    "ruhuma": {
        "umuzi/root": "humá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhumá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhuma",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba inyamaswa y'impumyi","Surnom d’un animal aveugle.","Nickname of a blind animal"
            ]
   
    },
    
    "ruhunde": {
        "umuzi/root": "huunde",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhuunde",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhunde",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu majyaruguru ya komini Cyungo muri perefegitura ya Byumba","Colline de la partie septentrionale de la commune de Cyungo dans la préfecture de Byumba.", "Hill in the northern part of the commune of Cyungo in the Byumba prefecture"
            ]
    },
    "igihunga": {
        "umuzi/root": "huunga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "igihuunga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "igihunga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyoba kiza mu umuntu ku buryo butunguranye bikamutera gukora ibintu hutihuti", "Panique"," a sudden great fear that causes hasty actions" 
            ]
  
   
    },
    "gahuzamiryango": {
        "umuzi/root": "huuzamiryaango",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gahuuzamiryango",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gahuzamiryango",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu wumvikanisha abandi cg imiryango","Conciliateur.", "Conciliator"
            ]
  
    },
    "amahwane": {
        "umuzi/root": "hwaáne",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "amahwaáne",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "amahwane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ugupfira rimwe kw'abantu cg ibintu bibiri birwana binganya imbaraga","Mort simultanée de deux combattants luttant à forces égales","Simultaneous death of two fighters battling at equal strengths"
            ]
    },
    "impahwane": {
        "umuzi/root": "hwaáne",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "impahwaáne",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "impahwane",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ibintu bihuje isura cg bingana mu mubyimba", "Objets identiques équivalents égaux.","equal objects."
            ]
   
    },
    "ruhwehwe": {
        "umuzi/root": "hweéhwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ruhweéhwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ruhwehwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umubeshyi","Surnom du menteur avisé.","Nickname of the shrewd liar."
            ]
   
    },
    "mahwera": {
        "umuzi/root": "hweerá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mahweerá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mahwera",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu wigaragaza uko atari mu by'ukuri nko kwirwaza atarwaye", "simulateur", "simulator"
            ]
    },
    "impuhwere": {
        "umuzi/root": "hweére",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "impuhweére",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "impuhwere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inzoga imaze nibura iminsi itatu","Bière vieille de trois jours au moins","Beer at least three days old"
            ]
  
    },
    
    "rwibobeza": {
        "umuzi/root": "iibobeeza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwiibobeeza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwibobeza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita imbwa yiba mu mazu", "Surnom d’un chien qui vole dans les maisons", "Nickname of a dog that flies into houses."
            ]
  
    },
    "urwicariro": {
        "umuzi/root": "iicariro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "urwiicariro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "urwicariro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwanda usigara ku mwambaro umuntu akura aho yicaye","Traces de saleté provenant d’un siège et adhérant à un vêtement.","Stains from a seat that cling to clothing."
            ]
   
    },
    "ubwiga": {
        "umuzi/root": "iiga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubwiiga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubwiga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amabyi y'umwana anyanyagiye ahantu hose", "Excréments d’enfant traînant un peu partout.","Children's droppings lying around everywhere."
            ]
    },
    "cyiganywa": {
        "umuzi/root": "iiganywá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyiiganywá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyiganywa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umunyabugugu utisukirwa", "Personne tellement avare qu’on n’ose pas l’aborder.","A person so stingy that one does not dare to approach them."
            ]
    },
    "rwigema": {
        "umuzi/root": "iigema",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwiigema",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwigema",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Intwari idatezuka mu byo yiyemeje","Guerrier brave et fiable qui agit conformément à ses décisions","A brave and reliable warrior who acts in accordance with his decisions."
            ]
        
   
    },
    "ibyiha": {
        "umuzi/root": "iiha",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ibyiiha",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ibyiha",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umushandiko w'imyiha bashishimisha impu", "Paquet de ces épines.","Bundle of those thorns."
            ]
    },
    "umwijuro": {
        "umuzi/root": "iijuuro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwiijuuro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwijuro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuva ahantu kw'abantu benshi", "Départ d’une foule.","Departure of a crowd."
            ]
        
        
    },
    "bwimba": {
        "umuzi/root": "iimba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bwiimba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bwimba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ugira umujinya udashira ukamutera kugwa nabi", "Une personne rancunière qui garde longtemps sa colère et qui de ce fait agit méchamment.","A resentful person who holds onto their anger for a long time and therefore acts maliciously."
            ]
   
    },
    "bwimbiza": {
        "umuzi/root": "iimbizá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bwiimbizá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bwimbiza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu wimbiza","Surnom d’une personne dont la colère dissimulée dure très longtemps.","Nickname of a person whose hidden anger lasts a very long time."
            ]
  
    },
    "rwimbyi": {
        "umuzi/root": "iimbyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwiimbyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwimbyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umukene utunzwe n'utwaka duke yeza","Pauvre qui ne vit que du maigre produit de sa terre.", "Poor person who lives only from the meager produce of their land."
            ]
   
    },
    "cyimeza": {
        "umuzi/root": "iimezá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "cyiimezá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "cyimeza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igiti cg ishyamba byimejeje bitari ibiterano","Arbre ou forêt qui a poussé spontanément","Tree or forest that has grown spontaneously"
            ]
    },
    "rwinera": {
        "umuzi/root": "iineerá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwiineerá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwinerá",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu udafite intege zo gukora na busa","Surnom de celui qui n’a pas la force de travailler", "Nickname for someone who lacks the strength to work."
            ]
    },
    "rwinuma": {
        "umuzi/root": "iinumá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwiinumá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwinuma",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuti uva muri karungu ukavura isundwe","Remède contre l’ozène",",Remedy for ozena"
            ]
  
    },
    "icyira": {
        "umuzi/root": "iira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "icyiira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "icyira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umutima utari hamwe umuntu aterwa no kuba ari wenyine","souffrance causée par l’isolement.","suffering caused by isolation."
            ]
   
   
    },
    
    "bwite": {
        "umuzi/root": "iité",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bwiité",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bwite",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu cy'umuntu yigenga ho","personelle","personal"
            ]
    },
    "abitira": {
        "umuzi/root": "iitira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "abiitira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "abitira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bufite nyirabarazana ho ikirangabwoko", "Clan qui a l’ibis bronzé pour totem.","Clan that has the bronze ibis as its totem"
            ]
    },
    "akitso": {
        "umuzi/root": "iitso",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "akiitso",
            "mu bwinshi/plural": "utwiitso"
        },
        "bandika/writing": "akitso",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Mu mwandiko akamenyetso baruhukira ho ariko batamanuye ijwi","virgule","comma"
            ]
   
    },
    "rwivanga": {
        "umuzi/root": "iivaanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwiivanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwivanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu wiroha mu bitamureba", "Surnom de celui qui se mêle des affaires qui ne le concernent pas","Nickname for someone who meddles in affairs that do not concern them"
        ]
    },
    "rwiziringa": {
        "umuzi/root": "iiziriingá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rwiiziriingá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rwiziringa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyatsi kitaramba byirinze kigeza kuri metero imwe na mirongo itanu z'uburebure","plantation dont les fruits du type capsule est densément couverts d’épines","Plantation whose capsule-type fruits are densely covered with spines"
            ]
    
    },
    "mujagamo": {
        "umuzi/root": "jágamo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mujágamo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mujagamo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara iyo ari yo yose isogororera mu umuntu akananuka bikabije ntikire","Toute maladie persistante et débilitante.","Any persistent and debilitating illness"
            ]
   
    },
    "kajangwe": {
        "umuzi/root": "jaangwé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kajjaangwé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kajangwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Isuka iri ho ishusho y'injangwe", "Houe importée de marque du chat.","Imported hoe branded with cat icon'"
            ]
    },
    "kajanja": {
        "umuzi/root": "jaanja",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kajaanja",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kajanja",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko imigozi y'ibijumba cg ibijumba ubwabyo byera kuri iyo migozi","Variété de boutures de patates ou patates de cette variété.","Variety of potato cuttings or potatoes of this variety" 
            ]
    },
     "rujaragata": {
        "umuzi/root": "jarágata",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rujarágata",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rujaragata",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ikivumvuri gifite ibara ry'ibihogo cg umukara","Insecte coléoptère de la famille des Scarabéidés","Beetle insect of the Scarabaeidae family"
            ]
   
    },
    "mujeri": {
        "umuzi/root": "jeri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mujeri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mujeri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'agasimba kaguguna kirinze kandi gakomeye","Ratel","honey badger"]
    },
    "bajeyi": {
        "umuzi/root": "jeéyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bajeéyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bajeyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwana wateteshejwe bikabije", "Enfant gâté.", "Spoiled child."
            ]
    },
    "majigo": {
        "umuzi/root": "jigo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "majigo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "majigo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " izina bahimba umuntu ufite amajigo manini","Surnom de qui a de fortes mâchoires.", "Nickname for someone with strong jaws."
            ]
    },
    "ubujiji": {
        "umuzi/root": "jiji",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ubujiji",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ubujiji",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwenge buke","Ignorance","Ignorance"
            ]
    },
    "rujijibura": {
        "umuzi/root": "jijibura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rujijibura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rujijibura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'igiti abagore bakoresha bahunika abagabo babo", "Plante utilisée en magie par les femmes pour soumettre leurs maris les dégoûter et les écarter des rivales", "separation herb"
            ]
    },
    
    "rujinja": {
        "umuzi/root": "jiinja",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rujjiinja",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rujinja",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikimonyo kinini kiba mu bindi","Grosse fourmi","Large brown ant"
            ]
 
    },
    "mujongo": {
        "umuzi/root": "joongo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mujoongo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mujongo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igufa rinini rihuza amatako yombi ari na ryo uruti rw'umugongo rushingiye ho","Os iliaque","iliac bone"
            ]

    },
    "mujuba": {
        "umuzi/root": "juba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mujuba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mujuba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Ubwoko bw'insina yera igitoki cy'inyamunyu","Variété de bananier dont le fruit épais et long n’est pas amer banane de cette variété.", "Variety of banana tree whose thick and long fruit is not bitter"
            ]
    },
    "kijugunya": {
        "umuzi/root": "jugunya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kijugunya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kijugunya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita inzara yateye mu Rwanda mu wa 1895","Famine qui a sévi au Rwanda en 1895", "Famine that struck Rwanda in 1895"
            ]
    },
    "kajumba": {
        "umuzi/root": "juumba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kajuumba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kajumba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'inzara yigeze gutera mu Bugoyi","Famine qui a sévi dans l’Ubugoyi", "Famine that struck in Ubugoyi"
            ]
    },
    "bujumbura": {
        "umuzi/root": "juumbura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bujuumbura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bujumbura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umurwa mukuru w'ubucuruzi w'uburundi","capitale commerciale du Burundi","commercial capital city of Burundi"
            ]
    },
    "kajura": {
        "umuzi/root": "juura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kajjuura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kajura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara y'icyubi ifata umuntu ikamwubika","Maladie subite qui terrasse rapidement", "Sudden illness that quickly overwhelms"
            ]
   
    },
    "majyanjyari": {
        "umuzi/root": "jyáanjyaári",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "majyáanjyaári",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "majyanjyari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu ufite ibirenge byaremajwe n'amavunja","Surnom d’une personne qui a les pieds déformés par les chiques","Nickname of a person whose feet are deformed by jigger flea"
            ]
    
   
    },
    "rukabukira": {
        "umuzi/root": "kabukira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukabukira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukabukira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'icyatsi gikura cyemye","Herbe annuelle dressée de la famille des Astéracées","An annual erect herb from the Asteraceae family"
            ]
    },
    "rukaburandekwe": {
        "umuzi/root": "kaburandekwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukaburandekwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukaburandekwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuhanga mu byo gutera icumu","Habile jeteur de lance.", "Skilled spear thrower."
            ]
    
    },
    "rukabyamurimbo": {
        "umuzi/root": "kabyamuriimbo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukabyamuriimbo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukabyamurimbo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu ukunda kurimba cyane ari ku mubiri ari no ku myambaro","Surnom d’une personne très propre à sa toilette ou à son habillement.", "Nickname of a person who is very clean and very stylish"
            ]
    },
    "agakabyo": {
        "umuzi/root": "kábyo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agakábyo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agakabyo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukurenza urugero mu buryo ubwo ari bwo bwose","Exagération", "Exaggeration"
            ]
    },
    "rukacarara": {
        "umuzi/root": "kacárara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukacárara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukacarara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umutsima w'amasaka masa","polenta de sorgho pur","pure sorghum polenta"
            ]
    },
    "rukagana": {
        "umuzi/root": "kagana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukagana",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukagana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inkotanyi ku rugamba","Guerrier qui lutte avec acharnement","Warrior who fights fiercely"
            ]
    },
    "igikagatiza": {
        "umuzi/root": "kagátiza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "igikagátiza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "igikagatiza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Agakabyo mu migenzereze cg mu myifatire","Affectation dans les agissements ou le comportement.","Affectedness in actions or behavior."
            ]
    },
    "agakage": {
        "umuzi/root": "kagé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agakagé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agakage",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "imimerere y'umuntu cg ikintu cyigize indakoreka", "Caractère acariâtre", "irascible character"
            ]
    },
      
    "rukamba": {
        "umuzi/root": "kaámba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukaámba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita imbwa y'inkazi", "Nom donné à un chien méchant.", "Name given to a nasty dog."
            ]
    },
    "rukambura": {
        "umuzi/root": "kaambuura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukaambuura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukambura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu icyo ari cyo cyose gica umuntu intege kimukura ku izima", "Correctif cause de changement", "Corrective cause of change"
            ]
    },
    "nkana": {
        "umuzi/root": "kána",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nkána",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nkana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'umuntu wo mu Cyingogo wabaye ho ku ngoma y 'umwami Kigeri Nyamuheshera","Nom d’un personnage de l’Icyingogo contemporain du roi Nyamuheshera","Name of a character from cyingogo contemporary with King Nyamuheshera."
            ]
    
   
   
    },
    "agakangato": {
        "umuzi/root": "káangaato",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agakáangaato",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agakangato",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ugukabya mu myifatire cg ishema rirenze urugero", "façon de faire fierté déplacée.", "misplaced pride"
            ]
    },
    "bikangu": {
        "umuzi/root": "kaángu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bikaángu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bikangu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu w'igihubutsi","Surnom de qui agit avec précipitation","Nickname for someone who acts hastily"
            ]
    },
    "rukanika": {
        "umuzi/root": "kanika",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "NA",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukanika",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bitirira umuntu udatinya aho rukomeye","Surnom d’un guerrier hardi", "Nickname of a bold warrior" 
            ]
    
    },
    "rukara": {
        "umuzi/root": "kara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi na komini biri mu majyaruguru ya perefegitura ya Kibungo","Colline et commune situées dans le nord de la préfecture de Kibungo.","Hill and commune located in the north of Kibungo Prefecture." 
            ]
    },
    "makara": {
        "umuzi/root": "kára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "makára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ibijumba","Variété de patate douce", "Variety of sweet potato"
            ]
    },
    "rukara": {
        "umuzi/root": "kára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inkekwe nini y'umuriro","Grand brasier", "Large brazier" 
            ]
    },
    "rukarakara": {
        "umuzi/root": "karakara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukarakara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukarakara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'itafari rinini bubakisha ryumye gusa batagombye kuritwika","Brique adobe espèce de grosse brique en terre séchée","Adobe brick" 
            ]
    },
    "mukarange": {
        "umuzi/root": "káraange",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukáraange",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukarange",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi na komini biri mu burengerazuba bwa perefegitura ya Byumba","Colline et commune de l’ouest de la préfecture de Byumba."
            ]
    },
    "rukarara": {
        "umuzi/root": "kárara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukárara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukarara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugezi uturuka mu ishyamba rya Nyungwe ukanyura muri komini Musebeya ukagenda ugabanya Ubufundu n'ubunyambiriri ukisuka muri Mwogo","Rivière qui prend sa source dans la forêt de Nyungwe, passe au sud de la commune de Musebeya et se jette dans la Rukarara","river that originates in the Nyungwe Forest, passes south of the Musebeya commune, and flows into the Rukarara"
            ]
   
        
    },
    "makayabo": {
        "umuzi/root": "kayaábo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "makayaábo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makayabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'ifi ibabuye irimo umunyu mwinshi","poisson fumé et salé","smoked and salted fish"
            ]
    },
    "rukayamigina": {
        "umuzi/root": "kaayamigina",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukaayamigina",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukayamigina",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba imfizi y'impongo","Surnom d’une antilope topi mâle","nickname of a male topi antelope"
            ]
    },
     "kazi": {
        "umuzi/root": "kazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Agace bongera ku izina ry'umuntu cg ry'inyamaswa kugira ngo byumvikane mu gitsina gore","Appendice servant à former quelques substantifs et dont le sens est féminin","Appendix used to form certain nouns and whose meaning is feminine"
            ]
   

    },
    "makende": {
        "umuzi/root": "keende",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "makeende",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makende",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Izina bahimba umwana watese", "Surnom d’un enfant gâté", "Nickname of a spoiled child."
            ]
    
   
    },
    "agakeneko": {
        "umuzi/root": "kéneko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agakéneko",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agakeneko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Agasuzuguro gakabije umuntu agaragariza undi","Fait de ne pas craindre du tout qqn", "The fact of not fearing someone at all" 
            ]
    },
    
    "gakenke": {
        "umuzi/root": "keenke",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gakeenke",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gakenke",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi uri muri komini Nyarutovu muri perefegitura Ruhengeri","Colline de la commune de Nyarutovu dans la préfecture de Ruhengeri.","Hill of the commune of Nyarutovu in the Ruhengeri prefecture."
            ]
    },
    
    "mikeno": {
        "umuzi/root": "keno",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mikeno",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mikeno",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Kimwe mu birunga by'urwanda" ,"Un des volcans du Rwanda.", "Un des volcans du Rwanda."
            ]
    },
    "rukenwa": {
        "umuzi/root": "keenwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukeenwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukenwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igisambo cyakuye agahu ku nnyo","Voleur avéré","Proven thief"
            ]
   
    },
    "rukenyamibyizi": {
        "umuzi/root": "kenyamibyizi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukenyamibyizi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukenyamibyizi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina abanyakazi bahaye umunsi wa kane w'icyumweru","Surnom que les employés donnent au jeudi","Nickname that employees give to Thursday"
            ]
    
    },
    "mukerarugendo": {
        "umuzi/root": "keerarugeendo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukeerarugeendo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukerarugendo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ukunda kujya mu ngendo cyane cyane iza kure","touriste.","tourist"
            ]
    },
    "rukererezabagenzi": {
        "umuzi/root": "keererezabageenzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukeererezabageenzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukererezabagenzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina abahigi bita umukeri kugira ngo utabatera umwaku"," Ronce terme d’évitement des chasseurs pour écarter la malchance","Bramble, a term of avoidance used by hunters to ward off bad luck."
            ]
    },
    "nketi": {
        "umuzi/root": "keéti",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nkeéti",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nketi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Iyo bavuga abacamanza ugushakisha bakurikiranye ukuri k'uko ibintu byakozwe cg byagenze badahari", "Enquête judiciaire","Judicial investigation"
        ]
    },
    "bukeye": {
        "umuzi/root": "keeye",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bukeeye",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bukeye",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ku munsi ukurikira uwo bavuga","Le lendemain","the following day."
            ]
    },
    "rukimirana": {
        "umuzi/root": "kimirana",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukimirana",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukimirana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Urusaku rw'ibintu bigongerera mu nda","Gargouillement abdominal","Abdominal rumbling"
        ]
    },
      "rukinga": {
        "umuzi/root": "kiinga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukiinga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukinga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu ufite urukinga", "Surnom de celui qui a un front saillant.","Nickname for someone with a prominent forehead"
            ]
    },
    "agakingamuyaga": {
        "umuzi/root": "kiingamuyaga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "agakiingamuyaga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "agakingamuyaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Urusika rw'iziko", "Cloison proche du foyer","Partition close to the hearth"
            ]
    },
    "mukingo": {
        "umuzi/root": "kiingo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukiingo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukingo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Komini iri mu burengerazuba bwa perefegitura ya Ruhengeri","commune de la prefecture Ruhengeri","commune of Ruhengeri prefecture"  
            ]
    },
    "mukinuzi": {
        "umuzi/root": "kinuzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukinuzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukinuzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                " Izina bahimba umuntu wica vuba", "Surnom du guerrier qui tue sur le coup.","Nickname of the warrior who kills instantly."
            ]
   
    },
    "mukobanya": {
        "umuzi/root": "kobánya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukobánya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukobanya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami wa cumi n'umunani w'urwanda ushingiye ku bucurabwenge ukabara usubira inyuma","Roi du Rwanda qui occupe le dix-huitième rang","King of Rwanda who holds the eighteenth rank"
            ]
    },
    "rukobora": {
        "umuzi/root": "kobora",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukobora",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukobora",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara y'inka ituma zunuka ho ubwoya","Maladie qui fait perdre les poils aux vaches.","Disease that causes cows to lose their hair."
        ]
 },        
    "mukobwa": {
        "umuzi/root": "koobwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukoobwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukobwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'amasaka","Variété de sorgho","Variety of sorghum"
            ]
    },
    "nkibyeze": {
        "umuzi/root": "ibyeéze",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nkibyeéze",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nkibyeze",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umunebwe ushaka kurya kandi adakora", "Personne paresseuse qui veut manger sans travailler.","lazy person"
            ]
    
    },
    
    "mukomarume": {
        "umuzi/root": "komarume",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukomarume",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukomarume",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'umunyabwira ukunda gutangira imirimo hakiri kare", "Personne zélée qui commence ses travaux de grand matin","Zealous person who starts their work early in the morning"
            ]
    },
    "rukomeza": {
        "umuzi/root": "komeza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukomeza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukomeza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'umunyabugugu utarekura", "Personne avare","Greedy person"
            ]
    },
    "bikomo": {
        "umuzi/root": "komo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bikomo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bikomo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Izina bahimba ihene ifite ibikomo", "Surnom d’une chèvre dont les cuisses sont couvertes de longs poils","Nickname of a goat whose thighs are covered with long hair"
        ]
    },
    "rukondo": {
        "umuzi/root": "koondo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukoondo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukondo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Umusozi na komini biri mu majyaruguru ya perefegitura ya Gikongoro","Colline et commune situées vers le nord de la préfecture de Gikongoro.","Hill and commune located in the northern part of the Gikongoro prefecture."
            ]
    
    },
    "nkongwa": {
        "umuzi/root": "koongwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nkoongwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nkongwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                " Ubwoko bw'agakoko kameze nk'agashorobwa cg nyamwihina kinjira mu bikenyeri cg mu bigori kakabimuungira mu murima","Diverses chenilles foreuses de la famille des Noctuidés qui vivent dans les tiges de graminées","Various boring caterpillars from the Noctuidae family that live in the stems of grasses."
            ]
    },
    "rukonyamakombe": {
        "umuzi/root": "konyamakoombe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular":" rukonyamakoombe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukonyamakombe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuhigi w'umuhanga cyane","Chasseur renommé","Renowned hunter"
               
            ]
    },
    
    "makorewa": {
        "umuzi/root": "koorewá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "makoorewá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makorewa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Icyuma bakoresha bakura imisumari","Tenailles","Pincers" 
            ]
    },
    "gikoro": {
        "umuzi/root": "koro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gikoro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gikoro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi na komini biri mu burasirazuba bwa perefegitura ya Kigali","Colline et commune situées à l’Est de la préfecture de Kigali.","Hill and commune located in the east of the Kigali prefecture."
            ]
    },
    
    "rukoro": {
        "umuzi/root": "koro",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukoro",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukoro",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ry'umuntu uvugwa mu mateka ngo wari umugome byahebuje","Nom d’un personnage historique qui était réputé extrêmement méchant.","Name of a historical figure who was known to be extremely wicked."
            ]
   
    },
    
    "rukubana": {
        "umuzi/root": "kuubána",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukuubána",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukubana",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu w'indwanyi kabuhariwe","Surnom du batailleur renommé","Nickname of the renowned fighter"
            ]
    },
    "rukubashyamba": {
        "umuzi/root": "kubashyaamba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukubashyaamba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukubashyamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu w'urukondokondo","Personne démesurément grande et qui marche en ployant sous son poids.","Excessively large person who walks while bending under their weight."
            ]
    },
    "nakabuba": {
        "umuzi/root": "ákabubá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nákabubá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nakabuba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu w'umunyarusaku","Surnom du criard.","Nickname of the screamer."
            ]
    },
    "nkumba": {
        "umuzi/root": "kuumbá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nkuumbá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nkumba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu majyaruguru ya perefegitura ya Ruhengeri wahaye izina komini uri mo","Colline et commune situées au Nord de la préfecture de Ruhengeri.","Hill and commune located north of the Ruhengeri prefecture."
        ]
    
   
    },
    "rukungerwa": {
        "umuzi/root": "kuungeérwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukuungeérwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukungerwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu utagira icyo atinya","personne intrépide.","intrepid person."
            ]
    },
    "mukungwa": {
        "umuzi/root": "kuungwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukuungwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukungwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Uruzi ruva muri Ruhondo rukisuka muri Nyabarongo","Grande rivière qui constitue le déversoir du lac Ruhondo dans la Nyabarongo.","Large river that serves as the outlet of Lake Ruhondo into the Nyabarongo."
            ]
    
    },
    "mukura": {
        "umuzi/root": "kura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ishyamba cyimeza rihuriwe ho n'amakomini atatu yo muri perefegitura ya Kibuye","forêt naturelle située entre trois communes de la prefecture Kibuye","natural forest located between three communes in Kibuye prefecture"
            ]
    },
    "nkuri": {
        "umuzi/root": "kuri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "nkuri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nkuri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi na komini biri mu burengerazuba bwa perefegitura ya Ruhengeri", "Colline et commune situées à l’Ouest de la préfecture de Ruhengeri.","Hill and commune located to the west of the Ruhengeri prefecture."
            ]
   
    },
    "rukurungirandosho": {
        "umuzi/root": "kuruungirandosho",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukuruungirandosho",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukurungirandosho",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ukunda ibirunge cyane","Amateur de mets assaisonnés de beurre","Enthusiast of dishes seasoned with butter"
            ]
    },
    
    "rukurura": {
        "umuzi/root": "kurura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukurura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukurura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imwe mu nyami z'i Gisaka","Nom de l’un des tambours dynastiques de l’Igisaka","Name of one of the dynastic drums of the Igisaka"
            ]
    },
    "mume": {
        "umuzi/root": "mee",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mumee",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mume",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Urutoke rwo hagati y'agahera na musumbazose", "Annulaire quatrième doigt","Ring finger"
            ]
    },
    "rukuruzi": {
        "umuzi/root": "kuruzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rukuruzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rukuruzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ububasha ibintu bimwe isi yifite mo butuma bikurura ibindi byishyira","Gravitation terrestre attraction universelle attraction d’un aimant","Earth's gravity,attraction of a magnet"
            ]
    },
    "mukushi": {
        "umuzi/root": "kuushi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukuushi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukushi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igikoresho basokoresha umusatsi","Démêloir peigne","Detangling comb"
            ]
    },
    "gakushwa": {
        "umuzi/root": "kuushwá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "gakuushwá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "gakushwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inyamaswa ihora irwana","Animal batailleur","Fighting animal"
            ]
    },
    "mukuta": {
        "umuzi/root": "kuuta",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mukuuta",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mukuta",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Uruhande runyerera rw 'igifu cy'inyamaswa", "Partie lisse de l’estomac d’une bête","Smooth part of an animal's stomach"
            ]
    },
    "makuzungu": {
        "umuzi/root": "kuzuungu",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "makuzuungu",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makuzungu",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubwoko bw'ikimodoka kinini gishobora gutwara imizigo", "Camion à remorque","Trailer truck"
            ]
    },
    "bikwa": {
        "umuzi/root": "kwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": " bikwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bikwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umugizi wa nabi birengeje urugero", "Pers0nne méchante à l’excès","Excessively malicious person"
            ]
    },
    "makwakwa": {
        "umuzi/root": "kwaakwa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular":"makwaakwa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makwakwa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita inguge iyo ari yo yose",   "Surnom du singe","Nickname for a monkey"
            ]
    },
    "makwakwanya": {
        "umuzi/root": "kwaakwáanya",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "makwaakwáanya",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makwakwanya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'umunyambaraga cg umunyabwira","Personne très forte","strong person"
            ]
    
    
    },
    "makwindigiri": {
        "umuzi/root": "kwiindigiri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "makwiindigiri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "makwindigiri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba igicinyigiri","Surnom donné à une personne petite et grosse.","Nickname given to a short and stout person"
            ]
    
    },
    "kumanuka": {
        "umuzi/root": "mánuká",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kumánuká",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kumanuka",
        "icyiciro/pos": [
            "verb",
            "inshinga"
        ],
        "igisobanuro/meaning": [
            
                "kugana hepfo", "descendre", "descend"
            ]
   
    },
    "kamarampaka": {
        "umuzi/root": "márampáka",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kamárampáka",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamarampaka",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ijambo umuntu avuga abari bashyamiranye bose bakumvikana. amatora yo guhindura itegeko rikomeye","Paroles de réconciliation.Referandum","Words of reconciliation.Referandum"
            ]
    },
    "rumarampamba": {
        "umuzi/root": "marampaamba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rumarampaamba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rumarampamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umunsi wa gatanu mu mvugo y'abanyakazi", "Terme par lequel les employés désignent le vendredi","Term by which employees refer to Friday"
            ]
    
    },
    "kimaranzara": {
        "umuzi/root": "maranzara",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kimaranzara",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kimaranzara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimba umuntu ukize akamenya n'abandi", "Surnom donné à un riche généreux","Nickname given to a generous rich person"
            ]   


    },
    "kamaratete": {
        "umuzi/root": "marateete",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kamarateete",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamaratete",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu kigoboka umuntu kikamukura mu kaga","Moyen auquel on recourt pour se tirer d’une difficulté.", "means one resorts to in order to get out of a difficulty"
            ]
    },
    "kimari": {
        "umuzi/root": "mari",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kimari",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kimari",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "umuntu wica imbaga cg utera abantu benshi umwaku bakarimbuka","personne qui tue une masse de gens","A scourge that kills a mass of people"
            ]
   
    },
    "kimatuzi": {
        "umuzi/root": "maatuuzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kimaatuuzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kimatuzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bahimbira impyisi ko icyo ifashe igikura ho inyama byanze bikunze", "Surnom donné à l’hyène", "Nickname given to the hyena"
            ]
    },
    "kamena": {
        "umuzi/root": "ména",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kaména",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamena",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwezi kwa cumi k'umwaka wa kinyarwanda", "sixième lune de l’année rwandaise","sixth moon of the Rwandan year"
            ]
    },
    "imenange": {
        "umuzi/root": "ménaangé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "iménaangé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imenange",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ubushingwe bw'ikintu bamenanze","Débris fragments grossiers d’un objet concassé","Coarse debris fragments of a crushed object"
            ]
   
    },
    "bamenya": {
        "umuzi/root": "menyá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "bamenyá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "bamenya",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu wihaye kumenya byose","Personne qui prétend tout savoir prétentieux","person who pretends to know everything"
            ]
    },
    "mamesa": {
        "umuzi/root": "mesa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "mamesa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "mamesa",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ubwoko bw'umwumbati utarura w'umuhondo kandi ukaryoha","Variété de manioc doux de teinte jaunâtre et de bon goût.","Variety of sweet cassava with a yellowish hue and good taste."
            ]
    },
    "rumeza": {
        "umuzi/root": "meza",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rumeza",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rumeza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwami w'urwanda bavuga mu bwiru ariko akaba atazwi mu mateka","Roi du Rwanda relaté dans le rituel dynastique mais inconnu de l’histoire.", "King of Rwanda mentioned in the dynastic ritual but unknown to history."
            ]
    },
    "ameza": {
        "umuzi/root": "méezá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "améezá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ameza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igikoresho gikoze mu giti cg mu cyuma gifite uruhande rwo hejuru rushashe kandi rugeretse ku maguru ","Table", "Table"
            ]
    },
    "kimezamiryango": {
        "umuzi/root": "mezamiryaango",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kimezamiryaango",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kimezamiryango",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu ukomokwa ho n'imiryango myinshi", "Ancêtre éponyme de plusieurs lignages", "Eponymous ancestor of several lineages"
            ]
    },
    "asanzwe": {
        "umuzi/root": "sáanzwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "asáanzwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "asanzwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                " Ku buryo bumenyerewe","D’ordinaire habituellement.","habitual"
            ]
    },
    "imongi": {
        "umuzi/root": "moongi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "imoongi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "imongi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ingwa yera de","Kaolin très blanc", "Very white kaolin"
            ]
    },
    "kamonyi": {
        "umuzi/root": "monyi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kamonyi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamonyi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Taba wahaye izina paruwasi y'abagatorika ihubatswe", "Colline et paroisse catholique de la commune de Taba.","Hill and Catholic parish of the municipality of Taba."
            ]
    
    },
    "kamwaga": {
        "umuzi/root": "mwaaga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kamwaaga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kamwaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu w'inkengu","Personne très adroite très subtile", "Very skillful person"
            ]
    },


    "umwe": {
        "umuzi/root": "mwé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umwé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikimenyetso cyandika umubarwa", "Chiffre un", "digit one."
            ]
    },
    "rimwe": {
        "umuzi/root": "mwé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "rimwé",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "rimwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inshuro yihariye iri yonyine","Une fois.","Once"
            ]
    },
    "kimwe": {
        "umuzi/root": "mwé",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kimwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kimwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
                "Ku buryo busa","similaire","Similarly"
            ]
    },
    "runaba": {
        "umuzi/root": "naaba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "runaaba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "runaba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini ya Butaro wahaye izina paruwasi y'abagatorika uri mo","Colline et paroisse catholique de la commune de Butaro","Hill and Catholic parish of the commune of Butaro"
            ]
 
    },
    "kunagura": {
        "umuzi/root": "náguurá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "náguurá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nagura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "gucura bundi bushya", "reforger à neuf.","refurbish"
        ]
  
    },
    "kanama": {
        "umuzi/root": "náama",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kanáama",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kanama",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komine yitwa ityo muri perefegitura ya Gisenyi","Colline de la préfecture de Gisenyi","Hill in Gisenyi prefecture"
            ]
   
    },
    "inamba": {
        "umuzi/root": "naámba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inaámba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inamba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umururumba","Cupidité", "insatiable desire for goods" 
            ]

    },
    "runanga": {
        "umuzi/root": "naanga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "runaanga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "runanga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Akagezi kisuka muri Nyabugogo hagati ya za komini Rutare na Buyoga","Rivière qui se jette dans la Nyabugogo entre les communes de Rutare et de Buyoga.","River that flows into the Nyabugogo between the communes of Rutare and Buyoga"
            ]
    },
    "runangura": {
        "umuzi/root": "naangura",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "runaangura",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "runangura",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umurwanyi wica adasambishije","Guerrier qui tue d’un coup", "Warrior who kills in one strike"
            ]
    },
    "munanguzi": {
        "umuzi/root": "náanguzi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "munáanguzi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "munanguzi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu cyose gishobora kwica ku buryo bugubangura ariko kitari intwaro", "Tout ce qui peut tuer d’une manière violente sauf les armes.","Everything that can kill in a violent manner except weapons"
            ]
    
    },
    "minani": {
        "umuzi/root": "naáni",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "minaáni",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "minani",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina ababyeyi bakunda kwita umwana uvutse ku mbyaro ya munani", "Nom fréquemment donné au huitième enfant d’une famille.","Name frequently given to the eighth child of a family"
            ]
    
    },
    "inarabyaye": {
        "umuzi/root": "nárabyáaye",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inárabyáaye",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inarabyaye",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuba warabyaye ukagira abana","Le fait d’avoir engendré des enfants","The fact of having given birth to children" 
            ]
    },
    "inarahabaye": {
        "umuzi/root": "nárahabáaye",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inárahabáaye",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inarahabaaye",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuba warabaye ahantu ukahatinda","Le fait d’avoir vécu longtemps à un endroit d’y traîner.","The fact of having lived a long time in a place and lingering there"
            ]
    },
    "inarambaye": {
        "umuzi/root": "náraambaye",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ináraambaye",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inarambaye",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuba warigeze gukenuka ku myambaro","Le fait d’avoir eu beaucoup de vêtements dans le passé","The fact of having had many clothes in the past"
            ]
    },
    "inarashatse": {
        "umuzi/root": "nárasháatse",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inárasháatse",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inarashatse",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukuba warashatse bikaba byakugirira akamaro cg byagutera ibyago","Fait d’être marié avec les conséquences bonnes ou mauvaises que cela peut comporter.","The fact of being married with the good or bad consequences that it may entail"
            ]
    },
    "umugabo": {
        "umuzi/root": "uumugabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "uumugabo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umugabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "ikinyuranyo cy'umugore","homme","a man"
            ]
    },
    "kanazi": {
        "umuzi/root": "nazi",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kanazi",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kanazi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini ya Kanzenze","Colline de la commune Kanzenze","Hill in Kanzenze commune"
            ]
   
    },
    "ikinege": {
        "umuzi/root": "nege",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "runege",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "runege",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwana umwe rukumbi","only child","enfant unique"
        ]
    },
    "binego": {
        "umuzi/root": "négo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "binégo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "binego",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwe mu bahungu ba Ryangombe wari intwari cyane","Un des fils de Ryangombe qui était très courageux.","One of the sons of Ryangombe who was very courageous"
            ]
    },
    "ineke": {
        "umuzi/root": "neké",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ineké",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ineke",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara y'inka iyitera kuramburura","Espèce de maladie de la vache qui cause l’avortement","A type of disease in cows that causes abortion"
            ]
    },
    "maneko": {
        "umuzi/root": "neeko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "maneeko",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "maneko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umukozi ushinzwe kugenzura rwihishwa ibikorwa bibangamiye ubutegetsi","Agent de la sûreté de l’état.","intelligence agent"
            ]
    },
    "nemba": {
        "umuzi/root": "néemba",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "néemba",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "nemba",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi uri muri komine Nyarutovu wubatse ho paruwasi y'abagatorika", "Colline et paroisse de la commune de Nyarutovu.","Hill and parish of the municipality of Nyarutovu"
            ]
    },
    "inenesi": {
        "umuzi/root": "néeneési",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inéeneési",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inenesi",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ukwinemfaguza ukarya cg ukanywa usa n'udashaka", "Dédain fantaisie manifestée en buvant ou en mangeant"," disdainful fancy expressed while drinking or eating"
            ]
    
    },
    "inengere": {
        "umuzi/root": "neéngeere",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ineéngeere",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inengere",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Inyama n'imitsi y'ijosi munsi y'irugu","Muscles du cou sous la nuque.","Muscles of the neck under the nape"
            ]
    
    },
    "runete": {
        "umuzi/root": "nete",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "runete",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "runete",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Ikintu cyacengewe mo n'amazi","Chose imprégnée d’eau.", "Thing soaked in water"
            ]
    },
    "ineza": {
        "umuzi/root": "néezá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inéezá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ineza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Igikorwa cyiza umuntu akorera undi ngo kimugirire akamaro", "bienfaisance.","goodness"
            ]
    },
    "minigo": {
        "umuzi/root": "nigo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "minigo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "minigo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Indwara ibyimbisha imitwe y'intoki","Maladie qui fait enfler les bouts des doigts.","Disease that causes the tips of the fingers to swell"
            ]
   
    },
    "kinihira": {
        "umuzi/root": "nihira",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kinihira",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kinihira",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo muri komini Cyungo muri perefegitura ya Byumba","colline de la préfecture Byumba, commune Cyungo","Hill in Cyungo Commune, Byumba prefecture"
            ]
    },
    "ininda": {
        "umuzi/root": "niinda",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "iniinda",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "ininda",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Amazi yo mu gishanga anyenya gusa mu butaka","Eau suintant de la terre dans un marais", "Water seeping from the ground in a marsh"
            ]
    },
    "kanombe": {
        "umuzi/root": "noombe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kanoombe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kanombe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burasirazuba bw'umurwa mukuru uriho ikibuga cy'indege mpuzamhanga wahaye izina komine uri mo","Colline et commune de la préfecture de Kigali situées à l’est de la capitale et où se trouve l’aéroport international du Rwanda.","Hill and commune of the Kigali prefecture located to the east of the capital where the international airport of Rwanda "
            ]
    },
    "manoza": {
        "umuzi/root": "nozá",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "manozá",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "manoza",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu wakarimi keza","Flatteur.","Flatterer"
            ]
    },
    "nta": {
        "umuzi/root": "ntaa",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "ventaa",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "venta",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "impakanyi","Il n’y a pas de.","There is no"
            ]
    },
    "kinukabugabo": {
        "umuzi/root": "nuukabugabo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kinuukabugabo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kinukabugabo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Izina bita umuntu wishaririza agashaka kwigira igihangange","Surnom d’une personne qui prend des airs martiaux.","Nickname of a person who adopts a martial demeanor"
            ]
    },
    "inuko": {
        "umuzi/root": "nuuko",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inuuko",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inuko",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umwuka mwiza cg mubi ukomoka ku ikintu", "Odeur", "smell"
            ]
    
    },
    "inundwe": {
        "umuzi/root": "nuundwe",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "innuundwe",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inundwe",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imyaka yapfuuye ubusa kubera guhitira","denrées alimentaires endommagées parce que trop vieilles","foodstuffs damaged because they're old" 
            ]
    
    },

    "inweri": {
        "umuzi/root": "nweéri",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inweéri",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inweri",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Imisatsi iboshye", "Cheveux tressés.", "Braided hair" 
            ]
        },
    "inyabutembo": {
        "umuzi/root": "nyábutéembo",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inyábutéembo",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inyabutembo",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Insina ikomoka muri icyo gihugu","Variété de bananier provenant de cette région.", "Variety of banana plant originating from this region"
            ]
    },
    "munyaga": {
        "umuzi/root": "nyaga",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "munyaga",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "munyaga",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu majyepfo ya komini Rutonde muri perefegitura ya Kibungo","Colline de la commune de Tutonde dans la préfecture de Kibungo.","Hill of the commune of Tutonde in the Kibungo prefecture" 
            ]
    },
    "umunyagatorika": {
        "umuzi/root": "nyagatoriká",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "umunyagatoriká",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "umunyagatorika",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umuntu wo mu idini ry'abakirisitu b'abaroma", "Catholique","Catholic"
            ]
    
    },
    "inyakare": {
        "umuzi/root": "nyakare",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "inyakare",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "inyakare",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umutwe w'ingabo waremwe na Ndori","Compagnie militaire créee par le roi Ndori","Military company created by King Ndori" 
            ]
   
    },
    "kinyamakara": {
        "umuzi/root": "nyámakára",
        "basoma/phonetics": {
            " ": "NA",
            "mu buke/singular": "kinyámakára",
            "mu bwinshi/plural": "NA"
        },
        "bandika/writing": "kinyamakara",
        "icyiciro/pos": [
            "noun",
            "izina"
        ],
        "igisobanuro/meaning": [
            
                "Umusozi wo mu burasirazuba bwa perefegitura ya Gikongoro wahaye izina komini uri mo","Colline et commune situées dans l’est de la préfecture de Gikongoro.","Hill and commune located in the east of the Gikongoro prefecture"
            ]
            
        },
        "kanyamanza": {
            "umuzi/root": "nyamáanza",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kanyamáanza",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kanyamanza",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Indwara bamwe bemeza ko inanura amaguru y'umwana iyo nyina atambutse agatumbi k'inyamanza akimutwite","Maladie qui est censée faire maigrir magiquement les jambes du bébé quand sa maman encore enceinte enjambe le cadavre d’une bergeronnette.","A disease that is supposed to magically slim the legs of a baby when its mother, still pregnant, steps over the corpse of a wagtail."
                ]
            
        },
        "kinyamateka": {
            "umuzi/root": "nyámatéeká",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kinyámatéeká",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kinyamateka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu uvuga ibigambo cg ubara inkuru ntaceceke","Persone trop bavarde indiscrète","Someone too talkative and indiscreet"
                ]
            
        },
        "kinyami": {
            "umuzi/root": "nyami",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kinyami",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kinyami",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri perefegitura ya Byumba wahaye izina komini urimo","Colline et commune de la préfecture de Byumba.","Hill and commune of the Byumba prefecture."
                ]
       
        },
        "kanyanga": {
            "umuzi/root": "nyaanga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kanyaanga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kanyanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'inzoga ikaze cyane iva mu byuya by'ibyo baba bacaniriye nk'urwagwa, isukari","La boisson alcoolisée fermentée traditionnelle du Rwanda. Elle est fabriquée à partir de matières premières locales","traditional fermented alcoholic beverage made from local raw materials like cereals and banana fruit"
                ]
        },
        "inyarigina": {
            "umuzi/root": "nyarigina",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyarigina",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyarigina",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Amavuta baraguza","Graisse divinatoire.","Divinatory grease."
                ]
        },
        "minyaruko": {
            "umuzi/root": "nyáruko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "minyáruko",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "minyaruko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu udakunda kuba hamwe","Persone qui n’a pas l’habitude rester à un endroit","Person who is not used to staying in one place"
            ]
        },
        "inyatsi": {
            "umuzi/root": "nyaátsi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyaátsi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyatsi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Utwatsi duto","herbs fines","Fine herbs"
                ]
            
        },
        "inyatsi": {
            "umuzi/root": "nyaátsi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nyaátsi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nyatsi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                         "Ahantu hateye utwatsi twiza tugufi","Lieu où pousse du gazon pelouse","Place where lawn grass grows"
                ]
        },
        "inyendamuvano": {
            "umuzi/root": "nyeendamuvaano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyeendamuvaano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyendamuvano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwanduranyo wo gushaka impamvu zo kurwana","provocation","provocation."
                ]
            
        },
        "manyenga": {
            "umuzi/root": "nyeenga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "manyenga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'igitagangurirwa kinini kigira ubumara","Mygale grosse araignée venimeuse","a large venomous spider"
                ]
            
        },
        "manyenya": {
            "umuzi/root": "nyeenyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "manyeenyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "manyenya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'igifwera cyirabura kiba mu mitumba","Limace noire des bananiers","Black slug of banana plants"
                ]
            
        
        },
        "rinyoni": {
            "umuzi/root": "nyoni",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rinyoni",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rinyoni",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ibuye rikomeye cyane abacuzi bacurira ho","Espèce de pierre très dure servant d’enclume aux forgerons","Type of very hard stone used as an anvil by blacksmiths"
                ]
            
        },
        "kinyoteri": {
            "umuzi/root": "nyoteéri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kinyoteéri",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kinyoteri",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Kamwe mu dutara two mu mpande zombi z'imbere n'inyuma y'ibyuma bitwara abantu n'ibintu","Clignotant de véhicule automobile.","Vehicle turn signal"
            ]
        },                    
        "rwogabicu": {
            "umuzi/root": "oogabicu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rwoogabicu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rwogabicu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "indege","avion","airplane"
                ]
            
       
        },
        
        "ngunda": {
            "umuzi/root": "nguunda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nguunda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ngunda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ikirayi bwaturutse mu kigo cy'ubushakashatsi mu by'ubuhinzi kiri i Rubona rwa Ngunda","Variété de pomme de terre diffusée par l’Institut des cciences agronomiques à partir de son siège de Rubona","Variety of potato distributed by the institute of agronomic sciences from its headquarters in Rubona"
            ]
      
        },
        "bwome": {
            "umuzi/root": "oome",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bwoome",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bwome",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwanda ufata ku mubiri w'inka kubera amase n'amaganga yaryamyemo","Saleté provenant de la bouse et du pissat dans lesquels la vache s’est couchée et qui adhère aux poils.","Dirt from the dung and urine in which the cow has lain, sticking to its fur."
                ]
            
        },
        "rwona": {
            "umuzi/root": "ooná",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rwooná",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rwona",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Uburumbe bw'ubutaka","stérilité du sol","sterility of the soil"
                ]
            
        },
        "urwongezankoni": {
            "umuzi/root": "oongezankoni",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwoongezankoni",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "urwongezankoni",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu bahana ntiyisubire ho","Personne qui se moque du châtiment","Person who mocks punishment"
                ]
            
        },
        "cyonza": {
            "umuzi/root": "oonzá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "cyoonzá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "cyonza",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu gitera kunanuka cg gukena","Cause de maigreur de diminution ou d’appauvrissement.","Cause of thinness or impoverishment."
                ]
            
        },
        
        "ibyoshyo": {
            "umuzi/root": "ooshyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ibyoshyo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ibyoshyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu abantu baha agaciro kandi nta ko gifite","Chose dont on vante la valeur sans raison","Thing whose value is praised without reason"
                ]
            
       
        },
        
        "mipanga": {
            "umuzi/root": "paánga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mipaánga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mipanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'amashaza afite imitanyu yigondoye","Variété de petits pois à gousses recourbées","Variety of peas with curved pods"
                ]
            
        },
        "gapanga": {
            "umuzi/root": "paánga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gapaánga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gapanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                "Ubwoko bw'ifi yo muri Muhazi","Espèce de poisson du lac Muhazi","Species of fish from Lake Muhazi"
                ]
        },
        "maparamane": {
            "umuzi/root": "paramané",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "maparamané",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "maparamane",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igisenge cy'inzu gifite impande enye","Toit à quatre pans","Four-pitched roof"
                ]
        },
        
        "gapfura": {
            "umuzi/root": "pfuura",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gapfuura",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gapfura",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Indwara ifata mu mihogo igatera ibintu by'ibipfupfuri mu nkanka no ku rurimi","Mal de gorge accompagné d’inflammation","Sore throat accompanied by inflammation"
                ]
        },
        "gapica": {
            "umuzi/root": "pica",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gapica",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gapica",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Icyatsi cyo mu muryango w'amashu","Herbe de la famille des Brassicacées","herb of the Brassicaceae family"
                ]
        },
        "rupigapiga": {
            "umuzi/root": "pigapigá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rupigapiga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rupigapiga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umufundi utazi akazi","Artisan malhabile bricoleur maladroit","awkward handyman"
                ]
        },
        "maraba": {
            "umuzi/root": "raaba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "maraaba",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "maraba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bwa ruguru bwa perefegitura ya Butare wahaye izina komini urimo","Colline et commune situées dans le nord","Hill and commune located in the north"
                ]
            
        },
        "karaba": {
            "umuzi/root": "raaba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karaaba",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karaba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                    "Umusozi wo muri komini Karama","Colline de la commune Karama","Hill of Karama commune"
                ]
       
        },
        "indaragihe": {
            "umuzi/root": "raagihe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "indaraagihe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "indaragihe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igihe cy'ubu mu itondagura ry'inshinga","Temps présent dans la conjugaison.","Present tense in conjugation."
                ]
        },
        "karago": {
            "umuzi/root": "rago",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karago",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karago",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru ya perefegitura ya Gisenyi wahaye izina komini urimo","Colline et commune situées au Nord dans la préfecture de Gisenyi.","Hill and commune located in the North of the Gisenyi prefecture."
                ]
        },
        "murama": {
            "umuzi/root": "ramá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muramá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "murama",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burasirazuba bw'amajyepfo bwa perefegitura ya Gitarama wahaye izina komini urimo","Colline et commune situées dans le Sud","Hill and commune located in the South."
                ]
        },
        "karama": {
            "umuzi/root": "ramá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karamá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karama",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burasirazuba bwa perefegitura ya Gikongoro wahaye izina komini urimo","Colline et commune situées dans l’est dans la préfecture de Gikongoro.","Hill and commune located in the east of the Gikongoro prefecture."
                ]
        },
       
        "murambi": {
            "umuzi/root": "raámbi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muraámbi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "murambi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Mugambazi muri perefegitura ya Kigali","colline de la commune Mugambazi","Hill of Mugambazi commune"
                ]
        },
        "kirambo": {
            "umuzi/root": "raambo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiraambo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kirambo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Cyeru","colline de la commune Cyeru","Hill of Cyeru commune"
                ]
                
        },
        "birambo": {
            "umuzi/root": "raambo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "biraambo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "birambo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Bwakira","colline de la commune Bwakira","Hill of Bwakira commune"
                ]
        },
        "karambo": {
            "umuzi/root": "raambo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karaambo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karambo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru ya perefegitura ya Gikongoro wahaye izina komini urimo","Colline et commune du nord de la préfecture de Gikongoro.","Hill and commune in the north of the Gikongoro prefecture."
                ]
            
        },
        "kurambya": {
            "umuzi/root": "raámbya",
            "basoma/phonetics": {
                " ": "kuraámbya",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kurambya",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Ku buryo igihimba amaguru n'amaboko birambuye","En position étendue","In an extended position"
                ]
        },
        "karandiriye": {
            "umuzi/root": "raandiriye",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karaandiriye",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karandiriye",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ikimenyeshaminsi","Calendrier","Calendar"
                ] 
            
        },
        "karanganwa": {
            "umuzi/root": "raanganwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karaanganwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karanganwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu wagizwe icyamamare n'ibyo akora byaba byiza cg bibi","Persone rendue célèbre par ses actes bons ou mauvais.","Person made famous by their good or bad deeds"
                ]
        },
        "kurangaranga": {
            "umuzi/root": "ráangaaraang",
            "basoma/phonetics": {
                " ": "kuráangaaraanga",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kurangaranga",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kureba hirya no hino buhoro witegereza","Regarder lentement de tous côtés en observant.", "To look slowly in all directions while observing."
                ]
            
        },
        "karangaza": {
            "umuzi/root": "raangaaza",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karaangaaza",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karangaza",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umugezi uturuka muri pariki y'akagera ukisuka mu Kagera","Rivière qui prend sa source dans le Nord du parc national de l’Akagera et se jette dans l’Akagera.","A river that originates in the north of Akagera National Park and flows into the Akagera."
                ]
        },
        "kurangurura": {
            "umuzi/root": "raangurur",
            "basoma/phonetics": {
                " ": "kuraangurura",
                "mu buke/singular": "",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kurangurura",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gushyira ijwi hejuru","Elever la voix","To raise one's voice"
                ]
        },

        "kuranzika": {
            "umuzi/root": "raánzik",
            "basoma/phonetics": {
                " ": "kuraánzika",
                "mu buke/singular": "",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kuranzika",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gutara inyama ukazumisha zikabikwa","Boucaner de la viande pour en faciliter la conservation.","To smoke meat to facilitate its preservation."
                ]
        },
        "ikirarane": {
            "umuzi/root": "raárane",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ikiraárane",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ikirarane",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Cyarengeje igihe cyo gukorwa cg cyo gutangwa","Qui a dépassé le temps donné.","Who has exceeded the deadline"
                ]
        },
        "irarwe": {
            "umuzi/root": "rárwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "irárwe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "irarwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugucika intege guturutse ku nzara n'inyota cg urugendo rurerure","Epuisement dû à une faim accompagnée de soif ou à un long voyage.","Exhaustion due to hunger accompanied by thirst or a long journey."
                ]
         },
        "muratwa": {
            "umuzi/root": "raátwa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muraátwa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muratwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imwe mu ngoma z'ingabe","Nom propre de l’un des tambours dynastiques","Proper name of one of the dynastic drums"
                ]
        },
        "mirayi": {
            "umuzi/root": "raayi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "miraayi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mirayi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umugezi uri muri komini Muganza wisuka mu Kanyaru","Rivière qui coule dans la commune de Muganza et se jette dans l’Akanyaru.","River that flows in the Muganza commune and empties into the Akanyaru."
                ]
            
        },
        "karayi": {
            "umuzi/root": "raayi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karaayi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karayi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu cyuzuye ho umwanda","Chose crasseuse","Filthy thing"
                ]
        },
        "rurazi": {
            "umuzi/root": "raázi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruraázi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rurazi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ingurube ishaje kandi iryana","cochon âgé et méchant.","Old and mean pig"
                ]
        },
        
        "kamusemburo": {
            "umuzi/root": "museemburo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kamuseemburo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kamusemburo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu watwawe n'inzoga ntatangwe aho zahiye","Persone avide de bière","A person eager for beer"
                ]
        },
        "kirehe": {
            "umuzi/root": "rehe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kirehe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kirehe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Rusumo","Colline de la commune Rusumo","Hill located in Rusumo commune",
                ]
            
        },
        "rurema": {
            "umuzi/root": "rema",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rurema",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rurema",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bitira imana","Dieu","God"
                ]
        },
        "karema": {
            "umuzi/root": "réma",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karéma",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karema",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba umuntu waremaye","Surnom d’un infirme","Nickname of a disabled person"
                ]
            
        },
        "iremano": {
            "umuzi/root": "remano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "iremano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "iremano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ishyo ry'inka barema bakariha umushumba","Troupeau de vaches que l’on crée et que l’on confie à un vacher en chef.","A herd of cows that is established and entrusted to a chief herdsman."
                ]
            
        
        },
        "marembo": {
            "umuzi/root": "réembo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "maréembo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "marembo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba umuntu wakutse amenyo y'imbere","Surnom d’une personne qui a perdu les incisives","Nickname for a person who has lost their incisors"
                ]
            
        },
        "karemera": {
            "umuzi/root": "remeera",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karemeera",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karemera",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina ry'ubwami ryiswe umwami Rwaka","Nom dynastique du roi Rwaka","Dynastic name of King Rwaka"
                ]
            
       
        },
        "birenga": {
            "umuzi/root": "réenga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "biréenga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "birenga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyepfo ya perefegitura ya Kibungo wahaye izina komini urimo","Colline et commune situées dans le sud de la préfecture de Kibungo","Hill and commune located in the south of the Kibungo prefecture"
                ]
            
        },
        "inderengabaganizi": {
            "umuzi/root": "reengabaganizi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "indereengabaganizi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inderengabaganizi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umutwe w'ingabo waremwe n'umwami Musinga","Compagnie militaire formée par le roi Musinga.","Military company formed by King Musinga."
                ]     
        },
        "rurengamiganyiro": {
            "umuzi/root": "reéngamiganyiro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rureéngamiganyiro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rurengamiganyiro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu w'ingorwa batereye iyo utagira ikimwunganira","Personne extrêmement nécessiteuse sans secours","An extremely needy person without assistance"
                ]
        },
        "irengampame": {
            "umuzi/root": "réengampáme",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "iréengampáme",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "irengampame",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igihe batondagura mo inshinga bumvisha igikorwa cyabaye mu gihe cyabanjirije ikindi gihe bavuga na cyo cyahise","plus-que-parfait","past perfect tense"
                ]
         },
        "rurenge": {
            "umuzi/root": "reenge",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rureenge",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rurenge",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu wa kera Abarenge bakomotse ho","Ancêtre éponyme du lignage des Renge","Eponymous ancestor of the Renge lineage."
                ]
            
        },
        "mirenge": {
            "umuzi/root": "réenge",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "miréenge",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mirenge",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu w'icyamamare waba yari atuye ku Ntenyo akize byahebuje","Grand personnage qui aurait vécu à Ntenyo et qui est connu pour avoir été très riche","A great figure who is said to have lived in Ntenyo,known for having been very wealthy"
                ]
            
        },
        "karengera": {
            "umuzi/root": "réengerá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karengera",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyepfo ya perefegitura ya Cyangugu wahaye izina komini urimo","Colline et commune situées dans le sud de la préfecture de Cyangugu.","Hill and commune located in the south of the Cyangugu prefecture."
                ]
            
        
        },
        "murenguzi": {
            "umuzi/root": "réenguzi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muréenguzi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "murenguzi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inzara umuntu amarana igihe ikazamwica","Faim prolongée qui peut entraîner la mort","Prolonged hunger that can lead to death"
                ]
        },
        "karenzo": {
            "umuzi/root": "réenzo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karéenzo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karenzo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umwana uvutse ku mbyaro ya cumi n'imwe","Nom donné au onzième enfant","Name given to the eleventh child"
                ]
            
        },
        "irera": {
            "umuzi/root": "réra",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "iréra",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "irera",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Uburyo bwo kwenga amarwa akazashya bitinze","Mode de brassage de la bière de sorgho où la fermentation dure","Brewing method of sorghum beer where the fermentation lasts"
                ]
            
        },
        "karere": {
            "umuzi/root": "reere",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kareere",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karere",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Akazu gato ka gikene gashakaje ibirere","Petite hutte couverte de feuilles sèches de bananier généralement habitée par des pauvres.","Small hut covered with dry banana leaves, generally inhabited by poor people."
                ]
            
        },
        "marere": {
            "umuzi/root": "réeré",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "maréeré",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "marere",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Urutoke rukurikira igikumwe","Index doigt voisin du pouce","Index finger next to the thumb"
                ]
            
       
        },
        "uburezi": {
            "umuzi/root": "rezi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "uburezi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "uburezi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umurimo w'umurezi","Education","Education"
                ]
         },
        
        "karimanzira": {
            "umuzi/root": "rimanzira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karimanzira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karimanzira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umuntu uhora mu ngendo","Surnom donné à une personne qui est toujours en voyage.","A nickname given to a person who is always traveling" 
                ]
        },
        "kirimbi": {
            "umuzi/root": "riimbi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiriimbi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kirimbi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umugezi wisuka mu Kivu unyura muri komine Gatare ho muri Cyangugu","Rivière qui coule dans la commune de Gatare et se jette dans le lac Kivu.","The river that flows through the commune of Gatare and flows into Lake Kivu."
                ]
            
        },
             "kirimbuzi": {
            "umuzi/root": "riimbuzi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiriimbuzi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kirimbuzi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Indwara itera igatsemba abantu cg amatungo","Epidémie, fléau.","epidemic disaster"
                ]    
        },
        "karindwi": {
            "umuzi/root": "riindwi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kariindwi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "Karindwi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umubarwa ukurikira gatandatu", "chiffre sept","digit seven"
                ]
            
        },
        "kuringaniza": {
            "umuzi/root": "riinganiz",
            "basoma/phonetics": {
                " ": "kuriinganiza",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kuringaniza",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Gutuma ibintu bireshya","Faire en sorte que des choses aient la même hauteur.","To ensure that things have the same height."
                ]
            
        },
        "ruringaniza": {
            "umuzi/root": "riinganiza",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruriinganiza",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruringaniza",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina abanyakazi bahaye umunsi wa gatatu w'icyumweru","Nom par lequel les employés désignent le mercredi","The name by which employees refer to Wednesday."
                ]
            
        },
        "ikibiringanya": {
            "umuzi/root": "riinganyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ikibiriinganyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ikibiringanya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igihingwa kiribwa buboga kimera nk'urutoryi","Aubergine de couleur violette.","big eggplant of purple color"
                ]
        },
        "karamaguru": {
            "umuzi/root": "maguru",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karamaguru",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karamaguru",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu uhora mu ngendo","Personne qui voyage constamment","Person who travels constantly"
                ]
         },
        "bariranwa": {
            "umuzi/root": "riránwa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bariránwa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bariranwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inda y'umuntu ihora itumbye","Ventre toujours gros","Always a big belly"
                ]
         },
        "murizi": {
            "umuzi/root": "rizi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "murizi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "murizi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwana murizi","Enfant pleurnichard","Whining child"
                ]
            
        },
        "kiriziya": {
            "umuzi/root": "riziyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiriziyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kiriziya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umuryango nyobokamana","Eglise","Church"
                ]
            
        },
        "karizo": {
            "umuzi/root": "riizo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kariizo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karizo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'isuka y'agasa gato kandi karekare","Variété de houe","Variety of hoe"
                ]
         },
       
        "karonda": {
            "umuzi/root": "roonda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karoonda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karonda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Indwara y'inka ifata ku rurimi rukamera ho amahwa ikananirwa kurisha", "Maladie des vaches qui s’attaquent à la langue","fièvre aphteuse"
                ]
         },
        "uburoondwe": {
            "umuzi/root": "roondwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "uburoondwe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "uburondwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikoraniro ry'indondwe ziri ku nyamaswa","Ensemble des tiques d’un animal","All the ticks on an animal"
                ]
            
        },
        "irorero": {
            "umuzi/root": "rorero",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "irorero",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "irorero",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inka z'ibwami zanyazwe n'umwami Ndori","Troupeau de vaches razziées par le roi Ndori","A herd of cattle raided by King Ndori"
                ]
            
        },
        
        "ndorwa": {
            "umuzi/root": "rorwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ndorwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ndorwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imwe mu ntara zo hambere iri mu majyaruguru y'urwanda iherereye mo komini z'ubu za Butaro,Kivuye Cyumba Kiyombe na Muvumba","Ancienne région du Rwanda septentrional couvrant les communes actuelles de Butaro, Kivuye, Cyumba, Kiyombe et Muvumba.","Former region of northern Rwanda covering the current communes of Butaro, Kivuye, Cyumba, Kiyombe, and Muvumba."
                ]
            
        },
       
        "karuba": {
            "umuzi/root": "ruba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karuba",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karuba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'itabi rikomoka ahanini muri Kongo","Variété de tabac provenant de RDC.","Variety of tobacco from the DRC"
                ]
            
        },
        "irugaruga": {
            "umuzi/root": "rugaruga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "irugaruga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "irugaruga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Itorero rya mbere rya gisirikare ryo ku ngoma y'abadage","Première compagnie militaire à l’époque de la colonisation allemande.","First military company during the time of German colonization."
                ]
        },
    
        "kirungurira": {
            "umuzi/root": "ruungurira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiruungurira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kirungurira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umuntu udaseka uhora arakaye","Surnom d’une personne qui est toujours de mauvaise humeur","A nickname for a person who is always in a bad mood"
                ]
        },
        "karyabagome": {
            "umuzi/root": "ryáabagomé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "karyáabagomé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "karyabagome",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina ry'inkota ya Nyabingi","Nom de l’épée de Nyabingi","Name of the sword of Nyabingi"
                ]
            
        },
        "muryamo": {
            "umuzi/root": "ryáamo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muryáamo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muryamo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Icyorezo cyateye mu nka ku ngoma ya Rwabugiri ","épidémie bovine pendant la règne de Rwabugiri","cattle plague during Rwabugiri reign"
                ]
            
        },
        "kiryana": {
            "umuzi/root": "ryaaná",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiryaaná",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kiryana",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina ry'inzu y'ubwami yabaga mo abayozi n'abatetsi","Maison de la cour royale où travaillaient les gens chargés du lait les cuisiniers et d’autres domestiques.","House of the royal court where the people in charge of milk, the cooks, and other servants worked."
                ]  
        },
        
        "kiryango": {
            "umuzi/root": "ryaango",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiryaango",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kiryango",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umugezi uturuka mu majyepfo ya komini Mukingi ugatemba ugabanya komini Masango na Mushubati ukisuka muri Nyabarongo","Rivière qui prend sa source au sud de la commune de Mukingi coule entre les communes de Masango et de Mushubati et se jette dans la rivière Nyabarongo.","A river that originates in the south of the Mukingi commune flows between the communes of Masango and Mushubati and empties into the Nyabarongo River."
                ]
        },
        "uburyarya": {
            "umuzi/root": "ryaarya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "uburyaarya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "uburyarya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubushukanyi bubeshya undi bukamwemeza uko utari cg icyo utagira","Hypocrisie","Hypocrisy"
                ]
         },

        "masabano": {
            "umuzi/root": "sabano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "masabano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "masabano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu icyo ari cyo cyose umuntu atunga agisaba undi","Objet mendié","Object begged for"
                ]
            
        },
        "agasabayango": {
            "umuzi/root": "sábayaango",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasábayaango",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasabayango",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugucika intege agatima kakigosora","Défaillance physique sans évanouissement vertige","Physical failure without fainting"
                ]
            
        },
        "gisabo": {
            "umuzi/root": "saabo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gisaabo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gisabo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'igishyimbo","Variété de haricot","Variety of bean"
                ]
            
        },
        "gisagara": {
            "umuzi/root": "sagára",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "",
                "mu bwinshi/plural": "gisagára"
            },
            "bandika/writing": "gisagara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Ndora","Colline de la commune Ndora","Hill of Ndora commune"
                ]   
        },
        
        "misago": {
            "umuzi/root": "sáago",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "misáago",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "misago",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina ababyeyi bakunda kwita umwana wabo uvutse ari uwa cumi n'umwe","Nom donné généralement à l’enfant qui naît le onzième","Name generally given to the child born eleventh"
            ]
        },
        "igisaka": {
            "umuzi/root": "saká",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "igisaka",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "igisaka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Intara y'urwanda yo mu burasirazuba bw'amajyepfo muri perefegitura ya Kibungo","region de la prefecture Kibungo","region of Kibungo prefecture"
                   
                ]
            
        },
        "gisaka": {
            "umuzi/root": "saká",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gisaká",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gisaka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina ry'akayara kigeze gutera mu Gisaka ","Nom d’une petite famine qui a affecté l’Igisaka","Name of a small famine that affected Igisaka"
                ]
            
        
       
        },
        "rusake": {
            "umuzi/root": "saáke",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rusaáke",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusake",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita isake","Nom donné au coq","Name given to the rooster"
                ]
        },
        "agasamamagara": {
            "umuzi/root": "sámamágará",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasámamágará",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasamamagara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Akayoga cg uturyo bidahagije","Quantité de bière ou de nourriture insuffisante","Insufficient amount of beer or food"
                ]
            
        },
        "musambanano": {
            "umuzi/root": "sáambanano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musáambanano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musambanano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Gikomoka ku busambane","Né de relations sexuelles illégitimes.","Born of illegitimate sexual relations."
                ]
            
        
        },
        "musambira": {
            "umuzi/root": "saambira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musaambira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musambira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri perefegitura ya Gitarama wahaye izina komini urimo","Colline et commune de la préfecture de Gitarama.","Hill and commune of the Gitarama prefecture."
                ]
            
       
        },
        "agasamusamu": {
            "umuzi/root": "sámusámu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasámusámu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasamusamu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inzoga ihagije umuntu anywa akenda gusinda","Quantité de bière suffisante pour rendre qqn à moitié ivre.","Amount of beer sufficient to make someone half drunk."
                ]
            
        },
        
        "musanganya": {
            "umuzi/root": "saángaanya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musaángaanya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musanganya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "izina bitira inzoga ko ihuza abantu","Surnom donné à la bière parce qu’elle favorise les rencontres et l’amitié.","Nickname given to beer because it promotes gatherings and friendship."
                ]
            
        },
        "agasangiro": {
            "umuzi/root": "saangiro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasaangiro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasangiro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugusonga uwaguye ku rugamba","Fait d’achever qqn sur le champ de bataille.","Act of finishing someone off on the battlefield."
                ]
            
        },
        "masango": {
            "umuzi/root": "saango",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "masaango",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "masango",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bw'amajyepfo bwa perefegitura ya Gitarama","colline de la prefecture Gitarama","Hill of Gitarama prefecture"
                ]
            
        },
        
        "busapfu": {
            "umuzi/root": "sapfu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "busapfu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "busapfu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'insina","Variété de bananier","Variety of banana plant"
                ]
        },
        "busaro": {
            "umuzi/root": "sáro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "busáro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "busaro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Agasaro gato","Perle de petites dimensions","Small-sized pearl"
                ]
            
        },
        "musasa": {
            "umuzi/root": "sasa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musasa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musasa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bw'amajyaruguru bwa perefegitura ya Kigali","colline de la prefecture de Kigali rurale","Hill in prefecture of Kigali"
                ]
            
        },
        "busasamana": {
            "umuzi/root": "sásamáana",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "busásamáana",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "busasamana",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Rwerere hafi ya Rubavu muri perefegitura ya Gisenyi uri ho paruwasi ya gaturika yitwa ityo","Colline de la commune de Rwerere près de Rubavu dans la préfecture de Gisenyi et paroisse catholique qui y est établie.","Hill of the commune of Rwerere near Rubavu in the Gisenyi prefecture and the Catholic parish established there."
                ]
            
       
        },
        "gasate": {
            "umuzi/root": "saté",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasaté",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasate",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Indwara y'inka ifata mu matwi","Inflammation purulente de l’oreille d’une vache","Purulent inflammation of a cow's ear"
                ]
            
        },
        "rusatira": {
            "umuzi/root": "saatiira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rusaatiira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusatira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi uri mu majyaruguru ya perefegitura ya Butare witiriwe komini uherereyemo","Colline et commune situées dans le nord de la préfecture de Butare.","Hill and commune located in the north of the Butare prefecture."
                ]
            
        
        },
        "musatsi": {
            "umuzi/root": "satsi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musatsi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musatsi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu ufite umusatsi ugera hafi mu maso","Surnom de celui qui a les cheveux proches des sourcils.","Nickname for someone whose hair is close to the eyebrows."
                ]
         },
        "rusatsi": {
            "umuzi/root": "satsi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rusatsi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusatsi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu ufite umusatsi mwinshi udashokoje","Surnom de celui qui a une chevelure abondante et mal soignée.","Nickname for someone with abundant and unkempt hair."
                ]
            
        },
        "ubusaza": {
            "umuzi/root": "sáaza",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ubusáaza",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubusaza",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubukure bw'umuntu urengeje ikigero cy'ubuto","Vieillesse","Old age"
                ]
            
        },
        "musazi": {
            "umuzi/root": "sazi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musazi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musazi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'inzoga ikomeye cyane","Variété de bière très alcoolisée.","Variety of very alcoholic beer."
                ]
            
       
        },
        "igise": {
            "umuzi/root": "sé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "igisé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "igise",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inyota y'icyo umuntu yifuza","Vif désir forte envie convoitise.","Strong desire"
                ]
                },
        "musebeya": {
            "umuzi/root": "sebéya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musebéya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musebeya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri perefegitura ya Gikongoro wahaye izina ikomini urimo","Colline et commune de la préfecture de Gikongoro.","Hill and commune of the Gikongoro prefecture."
                ]
            
        
        
        },

        "gasemantambara": {
            "umuzi/root": "semantaambara",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasemantaambara",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasemantambara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu uhora ateranya abandi ashaka ko barwana","Semeur de discordes","Provocateur of discord"
                ]
            
        },
        "agasemerere": {
            "umuzi/root": "semérere",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasemérere",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasemerere",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Impamvu ituma abantu barwana inyanduruko y'umurwano cg y'intambara","Cause de dispute de bataille","Cause of dispute for battle"
                ]
            
        
        },
        "gisemyi": {
            "umuzi/root": "semyi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gisemyi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gisemyi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igihe cy'igikoronize","Epoque coloniale","Colonial era"
                ]
        },
        "bisenga": {
            "umuzi/root": "seenga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "biseenga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bisenga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyepfo ya komini Kabarondo muri perefegitura ya Kibungo","Colline du sud de la commune de Kabarondo dans la préfecture de Kibungo.","Hill in the south of the municipality of Kabarondo in the Kibungo prefecture."
                ]
            },
             "masenge": {
            "umuzi/root": "séenge",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "aséenge",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "asenge",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "mushiki wa se w'umuntu","tante paternelle.","paternal aunt."
                ]
            
        
        },
        "mubyara": {
            "umuzi/root": "byáará",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mubyáará",
                "mu bwinshi/plural": "babyáará"
            },
            "bandika/writing": "mubyara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwana wa mushiki wa se w'umuntu","Enfant de la soeur du père","child of the father's sister"
                ]     
        },
        "busengo": {
            "umuzi/root": "séengo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "buséengo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "busengo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Gatonde muri perefegitura ya Ruhengeri","Colline de la commune Gatonde, préfecture Ruhengeri","Hill located in Gatonde commune, Ruhengeri prefecture"
                ]
            
        
        },
        "rusenyanteko": {
            "umuzi/root": "séenyantéeko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruséenyantéeko",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusenyanteko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igisingizo cy'umurwanyi kabuhariwe","Surnom d’un grand guerrier","Nickname of a great warrior"
                ]
            
        },
        "gisenyi": {
            "umuzi/root": "seényi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "giseényi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gisenyi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bwa ruguru bw'urwanda ku Kivu muri komini Rubavu wahaye izina perefegitura yitwa ityo","Colline et ville du nord","Hill and city of the north."
                ]  
        },
        "agaseruzo": {
            "umuzi/root": "seruzo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agaseruzo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agaseruzo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Amagambo asembura umuntu","Paroles provocatrices","Provocative words"
                ] 
        },
        "gasetsa": {
            "umuzi/root": "setsa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasetsa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasetsa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru ya komini Kigarama perefegitura ya Kibungo","Colline du nord de la commune de Kigarama dans la préfecture de Kibungo.","Hill in the northern part of the Kigarama municipality in the Kibungo prefecture."
                ]
        },
        "gishaka": {
            "umuzi/root": "shaká",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gishaká",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gishaka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Uduheri tw'ubushita","Pustules de variole","Smallpox pustules"
                ]
            
        },
        "mushaka": {
            "umuzi/root": "sháka",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musháka",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mushaka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burasirazuba bwa komini Gishoma","Colline de l'est de la commune Gishoma","Hill in the east of Gishoma"
                ]
            
        },
        "mashami": {
            "umuzi/root": "shámi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mashami",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mashami",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Icyumweru gikurikirwa na Pasika","Dimanche des Rameaux","Palm Sunday"
                ]
            
        },
        "gishamvu": {
            "umuzi/root": "shaámvu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gishaámvu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gishamvu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri perefegitura ya Butare yahaye izina komini urimo","Colline et commune de la préfecture de Butare.","Hill and municipality of the Butare prefecture."
                ]
            
       
        },
        "bishangi": {
            "umuzi/root": "shaángi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bishaángi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bishangi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ihene ifite ubwoya burebure","Chèvre à poil long","Long-haired goat"
                ]
         },
        "gashara": {
            "umuzi/root": "shará",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasshará",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ibirayi","Variété de pomme de terre","Variety of potato"
                ]
            
       
        },
        "gashashara": {
            "umuzi/root": "shashára",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gashashára",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashashara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu uteranya undi ku umuntu umufite ho ubutegetsi","Semeur de discorde avec les supérieurs","Seeder of discord with superiors"
                ]
            
        },
        "bushati": {
            "umuzi/root": "sháati",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "busháati",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bushati",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwe mu mifuka y'igifu cy'inyamaswa","Feuillet partie de l’estomac des ruminants","a part of the stomach of ruminants"
                ]
            
        
        },
        "gishegesha": {
            "umuzi/root": "shegésha",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gishegesha",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gishegesha",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu icyo ari cyo cyose gitera umuntu kuzongwa","Cause d’épuisement extrême","Cause of extreme exhaustion"
                ]
            
        
        },
        "gashekembuzi": {
            "umuzi/root": "shekeembuzi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gashekeembuzi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashekembuzi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu uhata undi ibibazo ashaka kugira ingingo agera ho","Personne qui en soumet une autre à un interrogatoire approfondi","Person who subjects another to an in-depth interrogation"
                ]
            
        },
        "bushenge": {
            "umuzi/root": "shéenge",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bushshéenge",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bushenge",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi uri mu burasirazuba bwa komini Gisuma perefegitura ya Cyangugu","Colline de l’est de la commune de Gisuma dans la préfecture de Cyangugu.","Hill in the east of the Gisuma municipality in the Cyangugu prefecture."
                ]
            
        
       
        },
        "masheshe": {
            "umuzi/root": "sheshe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "masheshe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "masheshe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyepfo ya komini Nyakabuye perefegitura ya Cyangugu","Colline située au sud de la commune Nyakabuye dans la préfecture de Cyangugu.","Hill located south of the Nyakabuye municipality in the Cyangugu prefecture."
                ]
            
       
        },
        "mushikaki": {
            "umuzi/root": "shikaáki",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musshikaáki",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mushikaki",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inyama yokeje bayitunze ku gati","Brochette de viande","Meat skewer"
                ]
            
        
        },
        "gishinja": {
            "umuzi/root": "shiinjá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gishiinjá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gishinja",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu urega undi ibyo yakoze","Témoin à charge accusateur","Accusing witness"
                ]
            
        },
        "agashinyaguro": {
            "umuzi/root": "shinyaguro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agashinyaguro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agashinyaguro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugushunga umuntu umusekera mu byago yagze","Raillerie acerbe du malheur d’autrui","Bitter mockery of others' misfortune"
                ]
            
        },
        "mashira": {
            "umuzi/root": "shirá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mashirá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mashira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu wahoze ari umuhinza w'i Nduga mu gihe cya Kigeri I Mukobanya","Personnage historique qui était roi du Nduga et contemporain du roi du Rwanda Mukobanya","Historical figure who was the king of Nduga and a contemporary of the king of Rwanda, Mukobanya."
                ]
            
        },
        "rushitamyambi": {
            "umuzi/root": "shitamyaambi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rushitamyaambi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rushitamyambi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba umuhigi w'umuhanga","Surnom donné à un chasseur très habile","Nickname given to a very skilled hunter"
                ]
        },
        "gashobya": {
            "umuzi/root": "shobyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasshobyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashobya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu wananiranye ku myifatire ye mibi","Personne incorrigible","Incorrigible person"
                ]
            
        },
        "gashogoro": {
            "umuzi/root": "shogoro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gashogoro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashogoro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igihe cy'umwaka mu mvugo y'abahinzi gitangirana n'ugushyingo kikarangirana n' ukuboza","Période de l’année des agriculteurs commençant avec la lunaison","Period of the year for farmers starting with the lunar cycle."
                ]
            
       
        
        },
        "gashora": {
            "umuzi/root": "shoorá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gashoorá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashoora",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyepfo ya perefegitura ya Kigali mu karere k'ubugesera wahaye izina komini urimo","Colline et commune situées au sud de la préfecture de Kigali dans la région de l’Ubugesera","Hill and commune located south of the Kigali prefecture in the Ubugesera region"
                ]
            
        },
        "rushorera": {
            "umuzi/root": "shoréra",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rushoréra",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rushorera",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'inyoni yo mu ijoro","Engoulevent du Gabon","Gabonese nightjar"
                ]
            
        },
        "inshumbushanyo": {
            "umuzi/root": "shuumbuushanyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inshuumbuushanyo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inshumbushanyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu umuntu ahabwa bamushumbusha","Chose donnée ou reçue en dédommagement","Thing given or received as compensation"
                ]
            
        },
        "agashungero": {
            "umuzi/root": "shuungeero",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agashuungeero",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agashungero",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugushimishwa no kubona undi ari mu byago ukabimwereka","Dérision à propos des malheurs d’autrui.","Derision regarding the misfortunes of others"
                ]
            
        },
        "agashungo": {
            "umuzi/root": "shuungo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agashuungo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agashungo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Akamenyero kabi umuntu aterwa no gushyigikirwa cg no kutabwirwa","Mauvaise habitude à laquelle on est incité","Bad habit to which one is encouraged"
                ]
            
        },
        "ishusho": {
            "umuzi/root": "shusho",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ishusho",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ishusho",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imisusire y'umuntu cg y'ikintu","Physionomie aspect.","Physiognomy appearance."
                ]
        },
        "gishwati": {
            "umuzi/root": "shwaati",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gishwaati",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gishwati",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ishyamba rya cyimeza ryo muri perefegitura ya Gisenyi mu makomini Kayove Gaseke Kanama Giciye Karago na Mutura","Forêt naturelle située en préfecture de Gisenyi dans les communes de Kayove Gaseke Kanama Giciye Karago et Mutura.","Natural forest located in the Gisenyi prefecture in the municipalities of Kayove, Gaseke, Kanama, Giciye, Karago, and Mutura."
                ]
        },
        "gishya": {
            "umuzi/root": "shyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gishyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gishya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikitarakoreshwa","Neuf non encore employé","New"
                ]
            
        },
        "bishyashya": {
            "umuzi/root": "shyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bishyashyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bishyashya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "bitarakoreshwa","neuf","new"
            ]
        },
        "gashyantare": {
            "umuzi/root": "shyáantáre",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gashyáantáre",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashyantare",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukwezi kwa kabiri k'umwaka wa kinyarwanda","Deuxième lune de l’année traditionnelle rwandaise","Second moon of the traditional Rwandan year"
                ]
            
       
        },
        "mashyenderi": {
            "umuzi/root": "shyéendeéri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mashyéendeéri",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mashyenderi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwana wateteshejwe agapfa umutima ntabe yamenya guca akarimo","Enfant gâté","Pampered lazy child."
                ]
            
        },
        "abuterashyenzi": {
            "umuzi/root": "shyeenzi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "abuterashyeenzi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubuterashyenzi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imyitwarire y'inshyenzi","Attitude de plaisanterie","Joking attitude"
                ]
            
        },
        "igishyika": {
            "umuzi/root": "shyika",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "igishyika",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "igishyika",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umutima uhagaze umuntu aterwa n'ibyago","Inquiétude angoisse","Anxiety worry"
                ]
            
        },
        "gishyita": {
            "umuzi/root": "shyitá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gishyitá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gishyita",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bw'amajyepfo bwa perefegitura ya Kibuye","colline de la préfecture Kibuye","Hill of Kibuye prefecture"
                ]
        },
        "gashyuha": {
            "umuzi/root": "shyuuhá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gashyuuhá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gashyuha",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'imigozi y'ibijumba","Variété de tiges de patates","Variety of sweet potato stems"
                ]
            
        },
        "gasibanyamiryango": {
            "umuzi/root": "sibanyamiryaango",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasibanyamiryaango",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasibanyamiryango",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu uteranya abandi bakangana","Semeur de discorde","Seed of discord"
                ]
            
        },
        "gasibanyankora": {
            "umuzi/root": "sibanyankoora",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasibanyankoora",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasibanyankora",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Urumbeti rubaje mu ihembe","Trompette de corne","Horn trumpet"
                ]
            
        },
        
        "agasiga": {
            "umuzi/root": "siiga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasiiga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasiga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'umurishyo w'ingoma","Variété de batterie de tambours","Variety of drum set"
                ]
            
        },
        "bisigati": {
            "umuzi/root": "sigáati",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bisigáati",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bisigati",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Kwamama by'umuntu waburaniwe cg gukubita hirya no hino wabuze uko ugira ibintu","Ne savoir que faire","Not knowing what to do"
                ]
            
        },
        "nsigaye": {
            "umuzi/root": "sigaye",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nsigaye",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nsigaye",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umunyiginya ukomokwa ho n'umuryango wamwitiriwe", "Personnage du clan Nyiginya ancêtre éponyme d’un lignage","Character of the Nyiginya clan, eponymous ancestor of a lineage"
                ]
            
        },
        "masima": {
            "umuzi/root": "sima",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "masima",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "masima",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu ukuyengeye kandi ukomeye cyane","Personne bien en chair et forte.","Well-fleshed and strong person."
                ]
            
        },
        "rusine": {
            "umuzi/root": "siine",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rusiine",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusine",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita ikimasa cy'isine","Surnom d’un boeuf de couleur violacée.","Nickname of a purplish-colored bull."
                ]
            
        },
        "musinzirambugu": {
            "umuzi/root": "siinziirambugu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musiinziirambugu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musinzirambugu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'inzoka","Serpent non identifié","Unidentified snake"
                ]
            
        
        },
        "agasisibiranyo": {
            "umuzi/root": "siisibiranyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasiisibiranyo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasisibiranyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukuva ahantu cg ku ikintu ugenda ugarukirana","Mouvement répétés effectués en avançant et en reculant","Repeated movements made by moving forward and backward"
                ]
            
        
        },
        "gasogi": {
            "umuzi/root": "sogi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasogi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasogi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burasirazuba bwa komini Rubungo perefegitura ya Kigali","Colline de l’est de la commune de Rubungo dans la préfecture de Kigali.","Hill in the east of the municipality of Rubungo in the Kigali prefecture."
                ]
            
        },
        "nsogotano": {
            "umuzi/root": "sogootano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nsogootano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nsogotano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igitungwa biciye kuribwa","Animal domestique abattu pour la viande.","Domestic animal slaughtered for meat."
                ]
            
        },
        "rusoka": {
            "umuzi/root": "soká",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rusoká",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusoka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Indwara imera nk'umusonga ikunda gufata umugongo","Elancements localisés généralement dans le dos","Localized aches generally in the back."
                ]
             },
        "agasomborotso": {
            "umuzi/root": "soomborotso",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasoomborotso",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasomborotso",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Urwiyenzo","Provocation","Repeated provocation"
                ]
            
        },
        "gasongantebyi": {
            "umuzi/root": "soongantebyi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasoongantebyi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasongantebyi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umuntu utagirira impuhwe abari mu byago","Surnom donné à une pers qui se montre impitoyable envers ceux qui sont dans le malheur.","Nickname given to a person who is ruthless towards those who are in misfortune."
                ]
            
        },
        "gasongo": {
            "umuzi/root": "soongo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasoongo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasongo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umuntu muremure","une personne grande","tall person"
                ]
            
        
        },
        "busoro": {
            "umuzi/root": "soro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "busoro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "busoro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Gishamvu","colline de la commmune Gishamvu","Hill of Gishamvu commune"
                ]
            
        },
        "masotera": {
            "umuzi/root": "soterá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "masoterá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "masotera",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'imbunda ngufi ishobora gutwarwa mu mufuka","pistolet","handgun"
                ]
            
        },
        "agasuhero": {
            "umuzi/root": "suheero",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasuheero",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasuhero",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwiyabire butewe n'ubwoba cg n'indwara","Etat de qqn qui est envahi par le chagrin la peur ou la maladie.","State of someone who is overwhelmed by sorrow, fear, or illness."
                ]
            
       
        },
        "rusukiranya": {
            "umuzi/root": "sukiranya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rusukiranya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusukiranya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "izina bita umuntu ukunda gusukiranya ibigambo by'imburamumaro","Surnom d’une pers qui a l’habitude de parler beaucoup et de manière incohérente.","Nickname for a person who tends to talk a lot and in an incoherent manner."
                ]
            
        },
        "agasukiranyo": {
            "umuzi/root": "sukiranyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasukiranyo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasukiranyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Urukurikirane rw'abantu baza urwunge cg rw'inyamaswa cg rw'ibintu biza ku buryo bw'akungikanyo","Suite ininterrompue de personnes, d’animaux ou de choses.","Uninterrupted sequence of representations of animals or things."
                ]
            
        },
        "musukumo": {
            "umuzi/root": "sukumo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "musukumo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "musukumo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ikintu cy'igikangisho bashyira mu mirima irimo imyaka imwe n'imwe kugirango gikange inyoni zije kona","Epouvantail","Scarecrow."
                ]
            
        },
        "gisuma": {
            "umuzi/root": "suumá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gisuumá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gisuma",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bwa perefegitura ya Cyangugu","Colline située dand l'ouest de la prefecture Cyangugu","Hill located in the west of Cyangugu prefecture"
                ]
        },
        "rusumo": {
            "umuzi/root": "suumo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rusuumo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rusumo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                    "Komini yo mu burasirazuba bw'amajyepfo bwa perefegitura ya Kibungo","Commune située dans le sud de la prefecture Kibungo","Commune located in the south of Kibungo prefecture"
                ]
        },
        "agasurantambara": {
            "umuzi/root": "suurantaambara",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasuurantaambara",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasurantambara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukwiyenza ushaka kurwana","Provocation","Provocation"
                ]
            
        },
         "gasutsa": {
            "umuzi/root": "sutsa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gasutsa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasutsa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu urushya ku buryo adashobora kumvikana n'abandi","Pers intraitable.","Unyielding person."
                ]
            
        },
         "agasuzuguro": {
            "umuzi/root": "suuzuguro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agasuuzuguro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasuzuguro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Akageso umuntu agira kamutera gusuzugura abandi","Mépris","Contempt"
                ]
            
        },
        "gusya": {
            "umuzi/root": "sya",
            "basoma/phonetics": {
                " ": "gusya",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gusya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "kumenagura ikintu kikaba ifu","moudre","grind"
                ]
            
        },
        "gusyegera": {
            "umuzi/root": "syeeger",
            "basoma/phonetics": {
                " ": "gusyeegera",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gusyegera",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kwitseta kw'ikintu ku kindi bikabyara urusaku rubabaza mu matwi y'ubyumva","Grincer","To creak"
                ]
            
        },
        
        "gasyeti": {
            "umuzi/root": "syéeti",
            "basoma/phonetics": {
                " ": "gasyéeti",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gasyeti",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ingofero ya kigabo ifite urukinga","Casquette","Cap"
                ]
            
        },
        "gusyigiza": {
            "umuzi/root": "syiigiza",
            "basoma/phonetics": {
                " ": "gusyiigiza",
                "mu buke/singular": "",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gusyigiza",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kugaragariza umuntu agasuzuguro ku byo agutegetse gukora","Montrer à qqn qu’on est excédé de ses ordres","To show someone that you are fed up with their orders"
                ]
            
        },
        
        "guta": {
            "umuzi/root": "tá",
            "basoma/phonetics": {
                " ": "gutá",
                "mu buke/singular": "",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "guta",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kurekura ikintu kikagwa hasi","lâcher","drop."
                ]
            
        },
        "gatagara": {
            "umuzi/root": "tágara",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatágara",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatagara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Kigoma hagati muri perefegitura ya Gitarama Hari ikigo kivurirwa abamugaye","La colline de la commune de Kigoma, au centre de la préfecture de Gitarama, abrite un centre de soins pour les personnes handicapées","he hill in Kigoma commune, in the center of Gitarama prefecture, has a healthcare center for disabled people"
                ]
            
        },
        "mutagatifu": {
            "umuzi/root": "taagatifu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutaagatifu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutagatifu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu cg ikintu bidafite inenge y'icyaha","Saint","Holy"
                ]
            
        },

        "itaka": {
            "umuzi/root": "taka",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "itaka",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "itaka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Uruhande rw'ubutaka rwo hejuru","Surface du sol","Surface of the ground."
                ]
            
        },
        "ntakaragasi": {
            "umuzi/root": "táakaragási",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ntáakaragási",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ntakaragasi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu cg ikintu banga kandi bifuriza ibyago biruta ibindi","Personne ou chose qu’on déteste à laquelle on souhaite les pires malheurs.","Person or thing that we hate and to which we wish the worst misfortunes."
                ]
            
        },
        "minkanda": {
            "umuzi/root": "inkáanda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "minkáanda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "minkanda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umugore munini","Surnom donné à une grosse femme.","Nickname given to a large woman."
                ]
            
        },
        "gitama": {
            "umuzi/root": "taama",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gitaama",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitama",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'itabi","Variété de tabac.","Variety of tobacco."
                ]
            
        },
        "katamobwa": {
            "umuzi/root": "támoobwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "katámoobwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "katamobwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu utisukirwa","Personne redoutable.","Formidable person."
                ]
            
        },
        "mutamu": {
            "umuzi/root": "tamu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutamu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutamu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita ihene ifite iryo bara","Chèvre de cette couleur.","Goat of this color."
                ]
            
        },
        "mutamu": {
            "umuzi/root": "tamu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutamu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutamu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu gifite ibara ry'umutamu","De couleur brun clair","Light brown in color"
                ]
            
        },
        "gatamura": {
            "umuzi/root": "támura",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatámura",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatamura",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Indwara y'bitungwa ibipfura igahindura uruhu rwabyo igikubati","Maladie du bétail qui fait tomber le poil et raidir la peau.","Animal disease that causes hair loss and skin stiffening."
                ]
            
        },
        "butamwa": {
            "umuzi/root": "tamwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "butamwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "butamwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri perefegitura ya Kigali uri hagati y'uruzi rwa Nyabarongo na za komini Kanombe Nyarugenge na Shyorongi Uwo musozi wahaye izina komini uri mo","NONE","NONE"
                ]
            
        },
        "gitana": {
            "umuzi/root": "tana",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gitana",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitana",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'ikiringiti cyera","Espèce de couverture de lit blanche.","Type of white bed cover."
                ]
            
        },
        "ibitandampaka": {
            "umuzi/root": "taandampaka",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ibitaandampaka",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ibitandampaka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ibintu ibyo ari byo byose bifutamye","Paroles incohérentes","abnormal behavior"
                ]
             },
        "mutanga": {
            "umuzi/root": "taanga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutaanga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Impongo y'inyagazi","Guib harnaché femelle","Female saddle-backed guan"
                ]
            
        },
        "rutanga": {
            "umuzi/root": "taanga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruttaanga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imfizi ifite iryo bara","Taureau de couleur rousse","Red-colored bull"
                ]
       
        },
        "rutangira": {
            "umuzi/root": "taangiira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruttaangiira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutangira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukwigarura cg ukwifata","capacité de se contenir.","Self-control"
                ]
            
        },
        "agatangwe": {
            "umuzi/root": "táangwé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agatáangwé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agatangwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugutanga abandi kugera ahantu","Fait d’arriver avant les autres","The act of arriving before others"
                ]
         },
        "gatanu": {
            "umuzi/root": "taanu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "taanu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "tanu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Iyo babara ikoraniro rigizwe n'abantu cg ibintu bine wongeye ho ikindi.","cinq","five" 
                ]
            
        },
        "gatanya": {
            "umuzi/root": "taanyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gataanyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatanya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ikintu gitanya abantu. abashakanye","divorce","divorce"
                ]
            
        },
        "rutanyabanya": {
            "umuzi/root": "tányabánya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rutányabánya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutanyabanya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu w'umuhanga mu gusambana","Surnom d’une personne très débauchée.","Nickname of a very debauched person."
                ]
            
        },
        "mutara": {
            "umuzi/root": "tára",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutára",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Rimwe mu mazina y'ubwami bw'ingoma Nyiginya ryitwaga umwami wimikirwaga kuba uw'ubukire ku nka","L’un des noms dynastiques des rois Nyiginya qui était porté par des rois vachers.","One of the dynastic names of the Nyiginya kings that was held by cattle kings."
                ]
        },
        "gitarama": {
            "umuzi/root": "taráma",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gitaráma",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitarama",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini Nyamabuye","colline de la commune Nyamabuye","Hill of Nyamabuye commune"
                ]
            
        },
        "mutarama": {
            "umuzi/root": "taráma",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutaráma",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutarama",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukwezi kwa mbere k'umwaka w'kinyarwaanda","Première lune de l’année rwandaise correspondant à janvier","First moon of the Rwandan year corresponding to January"
                ]
        },
        "rutare": {
            "umuzi/root": "táre",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rutáre",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutare",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyepfo ya perefegitura ya Byumba","Colline et commune situées dans le sud de la préfecture de Byumba","Hill and commune located in the south of the Byumba prefecture"
                ]
            
        },
        "gatare": {
            "umuzi/root": "táre",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatáre",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatare",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru ya perefegitura ya Cyangugu wahaye izina komini urimo","Colline et commune situées dans le nord de la préfecture de Cyangugu.","Hill and commune located in the north of the prefecture."
                ]
            
        },
        "butare": {
            "umuzi/root": "táre",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "butáre",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "butare",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wubatse ho umugi wo mu majyepfo y'urwanda muri komini ya Ngoma","Colline sur laquelle est bâtie une ville au sud du Rwanda dans la commune de Ngoma","Hill on which a city is built in the south of Rwanda in the commune of Ngoma; cture bordered by Gikongoro and Gitarama"
                ]
            
        
            
        },
        "rutarindwa": {
            "umuzi/root": "táriindwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rutáriindwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutarindwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwami w'urwanda utemerwa n'ubucurabwenge,Izina ry'ubwami akaba Mibambwe","Le roi du Rwanda non reconnu par l'historiographie, dont le nom royal est Mibambwe","The King of Rwanda not recognized by historiography, whose royal name is Mibambwe"
                ]
            
        },
        "matarisi": {
            "umuzi/root": "tárisi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "matárisi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "matarisi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu utwara inzandiko azivana ku iposita azshyira bene zo","employé de la poste qui porte le courrier aux destinataires.","employee of the post office who delivers mail to recipients."
                ]
            },
                
        "matarisi": {
            "umuzi/root": "tarisi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "matarisi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "matarisi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'umukino w'abana bakina biruka basimburana","Course de relais pratiquée par les enfants","Relay race practiced by children"
                ]
            
        
        },
        "matati": {
            "umuzi/root": "taáti",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mataáti",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "matati",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umuntu w'umuhemu bihebuje","Surnom d’une pers très malhonnête.","Nickname of a very dishonest person"
                ]
            
        },
        
        "ntazirano": {
            "umuzi/root": "taaziirano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ntaaziirano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ntazirano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Kigenekereza cg gishingiye ku biri ho ariko kitabyeruye","Ambigu équivoque reflétant la réalité","Ambiguous, equivocal, reflecting reality."
                ]
            
        },
        "mutebe": {
            "umuzi/root": "tébe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutébe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutebe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ihene nini cyane","Grosse chèvre.","Big goat."
                ]
            
        },
        "igitebwe": {
            "umuzi/root": "tebwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "igitebwe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "igitebwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umwete muke by'umuntu w'umunebwe","Lenteur d’un paresseux","Slowness of a sloth in movement"
                ]
            
        },
        
        "umutegano": {
            "umuzi/root": "teegano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umuteegano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umutegano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu umuntu abona yagitegewe","Chose acquise par pari.","Thing acquired by wager."
                ]
            
        },
        "agateganyo": {
            "umuzi/root": "téganyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agatéganyo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agateganyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ikintu gikorwa bategereje kuzabona ikindi gihamye kizagisimbura","provisoire","provisional"
                ]
            
        },
        "ubutegetsi": {
            "umuzi/root": "tégetsi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "abutégetsi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubutegetsi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ububasha bw'Umuntu utegeka","Autorité","Authority"
                ]
             },
        "gatemabagome": {
            "umuzi/root": "témabágomé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatémabágomé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatemabagome",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuhoro w'isereri abagaragu ba Nyabingi bita abagirwa bakoresha mu mihango","Serpette sans manche dont les officiants de Nyabingi dénommés","Handleless sickle used by the officiants of Nyabingi."
                ]
            
        },
        "gatemeri": {
            "umuzi/root": "teméri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gateméri",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatemeri",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inzu yo mu bitaro bashyira mo abapfu igihe bagitegereje kubahamba","Morgue","Morgue"
                ]
            
        },
        "mutemyi": {
            "umuzi/root": "témyi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutémyi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutemyi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igisebe kinini kigasha umuntu","Grande plaie qui affaiblit","Great wound that weakens"
                ]
            
        },
        "rutenderi": {
            "umuzi/root": "teenderi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruteenderi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutenderi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Mu migani imfizi yaje iherekeje inka za mbere ziva mu ngezi","Taureau légendaire qui accompagnait le premier troupeau sorti d’un lac.","Legendary bull that accompanied the first herd that emerged from a lake."
                ]
            
        },
        "ntendezi": {
            "umuzi/root": "teéndeezi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "teéndeezi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ntendezi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru ya komini Karengera muri perefegitura ya Cyangugu","Colline du nord de la commune de Karengera dans la préfecture de Cyangugu.","Hill in the north of the municipality of Karengera in the Cyangugu prefecture."
                ]    
        },
        "matene": {
            "umuzi/root": "tene",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "matene",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "matene",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'inyoni","oiseau de la famille des Ploceidae Vidua macroura.","a bird of the family Ploceidae, Vidua macroura."
                ]
            
        },
        "ntera": {
            "umuzi/root": "teerá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nteerá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ntera",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ijambo rijyana n'izina rikarivugaho ikintu","Adjectif","Adjective"
                ]
            
        },
        "gateranyabagabo": {
            "umuzi/root": "teeranyabagabo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatteeranyabagabo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gateranyabagabo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu ukunda gusibanya abandi","Personne qui aime semer la discorde","Person who loves to sow discord"
                ]
            
        },
        "umutererano": {
            "umuzi/root": "téereerano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umutéereerano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umutererano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu baterereza umuntu","Envoûtement lancé contre ou esprit hostile","a hostile spirit sent to someone."
                ]
            
        },
        "gitesi": {
            "umuzi/root": "teesi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "giteesi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitesi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wakurijwe ho izina rya komini yitwa ityo ikaba muri perefegitura ya Kibuye","Colline qui a donné son nom à la commune où elle se trouve dans la préfecture de Kibuye.","Hill that gave its name to the commune where it is located in the Kibuye prefecture."
                ]
            },
        "mutikuzi": {
            "umuzi/root": "tikuzi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutikuzi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutikuzi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusonga cg imbwa bifata mu gituza","Pointe de douleur à la poitrine","Sharp pain in the chest"
                ]
            
        },
        "mihaniro": {
            "umuzi/root": "ihaniro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mihaniro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mihaniro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba umuntu w'intabwirwa utagishobora kwigarura","Surnom donné à une pers incorrigible","Nickname given to an incorrigible person."
                ]
            
        },
        "agasyo": {
            "umuzi/root": "gasyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agasyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Intimba ishengura umuntu cyane","Chagrin terrible.","Terrible sorrow or Great grief."
                ]
            
        },
        "butimbo": {
            "umuzi/root": "tiimbo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "buttiimbo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "butimbo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'iteke","Variété de colocase.","Variety of taro."
                ]
            
        },
        
        "gitinywa": {
            "umuzi/root": "tiinywá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gitiinywá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitinywa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba umukoni kubera amakare y'amata yawo","Surnom donné à l’euphorbe","Nickname given to the spurge."
                ]
            
        },
        "ntirano": {
            "umuzi/root": "tiirano",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ntiirano",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ntirano",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu cyatiwe","Objet emprunté","Borrowed object"
                ]
            
        },
        "urutoki": {
            "umuzi/root": "toki",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urutoki",
                "mu bwinshi/plural": "intoki"
            },
            "bandika/writing": "urutoki",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ikiganza kiriho intoki","doigt","finger"
                ]
            
        },
        "madamu": {
            "umuzi/root": "mádaámu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mádaámu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "madamu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'imyumbati itarura","Variété de manioc doux.","Variety of sweet cassava."
                ]
            
        },
        "rutongo": {
            "umuzi/root": "toongo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruttoongo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutongo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bwa ruguru bwa perefegitura ya Kigali","Une montagne dans le nord-ouest de la province de Kigali.","A mountain in the northwest of the Kigali province"
                ]
            
       
        },
        "ntongwe": {
            "umuzi/root": "toongwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ntoongwe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ntongwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo muri komini yitwa ityo muri perefegitura ya Gitarama","Colline et commune situées dans la préfecture de Gitarama.","Hill and commune located in the prefecture of Gitarama."
                ]
            
        },
        "matorewa": {
            "umuzi/root": "toorewá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mattoorewá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "matorewa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Impapuro zanditse ho ikizwa ry'urubanza mu magambo ahinnye cg arambuye","Extrait ou copie de jugement.","Extract or copy of a judgment."
                ]
            
        },
        "rutorobozantenge": {
            "umuzi/root": "torobozanteenge",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rutorobozanteenge",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutorobozantenge",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusambanyi utigerera n'utwana dutoya", "Débauché qui ne respecte même pas les petits enfants.","Debauched person who does not even respect small children."
                ]
            
        },
        "bitorwa": {
            "umuzi/root": "toorwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bitoorwa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bitorwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba imwe mu mpanga iyo indi yapfuye","Surnom donné à l’un des jumeaux quand l’autre est mort.","Nickname given to one of the twins when the other has died."
                ]
            
        },
        "rutotezanzira": {
            "umuzi/root": "tootezanzira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rutootezanzira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutotezanzira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " izina bahimba mpyisi","Surnom de l’hyène.","Nickname of the hyena."
                ]
            
        },
        "gatoya": {
            "umuzi/root": "tooyá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatooyá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatoya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umwana umwe mu mpanga wavutse nyuma","Nom donné au jumeau né le second.","Name given to the twin born second."
                ]
            
        },
       
        "gutsikamira": {
            "umuzi/root": "tsikamir",
            "basoma/phonetics": {
                " ": "gutsikamira",
                "mu buke/singular": "NA",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gutsikamira",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "Kujya hejuru y'ikintu ugatsindagira","Faire peser son poids sur peser sur","To exert influence on"
                ]
            
        },
        "insinda": {
            "umuzi/root": "tsiinda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "insiinda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "insinda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ibintu inzuki zitarira mu nkongoro ntibyireme mo ubuki","Contenu avorté d’une alvéole ","Aborted content of a cell"
                ]
            
        },
        "gitsindayogi": {
            "umuzi/root": "tsiindayogi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gitsiindayogi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitsindayogi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'umugozi wera ibijumba ugakunda kurumbuka","Variété de tige de patate très fertile.","Variety of potato stem that is very fertile"
                ]
            
        },
          "agatunambwenu": {
            "umuzi/root": "mbweénu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agatunambweénu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agatunambwenu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugukoreshwa imirimo ivunanye kandi ubutaruhuka","Fait de vaquer sans relâche à des travaux durs.","The act of tirelessly attending to hard work."
                ]
            
        },
        "gitumo": {
            "umuzi/root": "tuumo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gituumo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitumo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "gutungura cyangwa gufata umuntu atiteguye","prendre sur le fait","taking someone by surprise"
                ]
            
        },
        "gutumura": {
            "umuzi/root": "tuumuura",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gutuumuura",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gutumura",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "gucucura","Soulever de la poussière","to stir up dust"
                ]
            
        },
        "gatumwa": {
            "umuzi/root": "tumwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatumwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gatumwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Icyago umuntu atazasimbuka","Malheur fatal danger inévitable.","inevitable danger."
                ]
            
        },
        "rutunda": {
            "umuzi/root": "tuunda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rutuunda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rutunda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita isake","Surnom du coq","Nickname of the rooster"
                ]
            
        },
        "butunda": {
            "umuzi/root": "tuunda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "butuunda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "butunda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inzoga yatazwe ahantu hakonje igashya yirondereza","Bière mise dans un lieu froid pour qu’elle ait une fermentation lente","Beer placed in a cold location for slow fermentation"
                ]
            
        },
        "ruturagara": {
            "umuzi/root": "turagara",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruturagara",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruturagara",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                "Inkuba hinda mu gihe imvura iba ishaka kugwa","Tonnerre qui se fait entendre peu avant une pluie.","Thunder that is heard shortly before rain."
                ]
            
        },
        "gituranya": {
            "umuzi/root": "turánya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gituránya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gituranya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu gikura umuntu umutima cg kikamubuza uburyo","Chose qui effraie qui incommode qui dérange","Thing that frightens"
            ]
            
        },
        "gature": {
            "umuzi/root": "tuuré",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gatuuré",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gature",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ingeso y'imbyirukanano cg yabaye akarande ku muntu kera akaba atagishobora kuyicakaho","mauvaise habitude dont on ne peut pas se défaire.","a bad habit that one cannot get rid of"
                ]
            
        },
        "mutwa": {
            "umuzi/root": "twá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mutwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mutwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imandwa ibandwa n'Abatwa","Esprit de Bwatwa","Spirit of Batwa"
                ]
            
        },
        "gitwa": {
            "umuzi/root": "twá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "gitwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "gitwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Nk'Abatwa", "Agir à la manière des Twa","Act in the manner of the Twa"
                ]
            
        },
        
        "bitwenge": {
            "umuzi/root": "tweenge",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bitweenge",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bitwenge",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu ukunda guseka ubusa hato na hato", "Personne qui rit souvent et de rien.","Person who laughs often and at nothing."
                ]
            
        },

        "rwuburangeso": {
            "umuzi/root": "uuburangeso",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rwuuburangeso",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rwuburangeso",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu wadutsweho n'ingeso mbi","Personne qui vient de contracter un défaut","Person who has just incurred a defect"
                ]
            
        },
        "utwugarizo": {
            "umuzi/root": "uugarizo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "utwuugarizo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "utwugarizo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Mu kwandika utumenyetso bafungisha amagambo yavuzwe n'undí","Guillemets terminaux","closing quotation marks"
                ]
            
        },
        "utwuguruzo": {
            "umuzi/root": "uuguruzo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "utwuuguruzo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "utwuguruzo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Mu kwandika utumenyetso dutangira amagambo yavuzwe n'undí","Guillemets initiaux","Initial quotation marks"
                ]
            
        },
        "agacuho": {
            "umuzi/root": "uuho",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "agacuuho",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "agacuho",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    " Umunaniro ateerwa n' urugeendo rurerure cg imirimo","épuisement résultant d’un voyage ou d’une activité intense","Fatigue caused by travel or intense activity"
                ]
            
        },
        "mvaruganda": {
            "umuzi/root": "váarugaánda",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mváarugaánda",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mvaruganda",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu gishya gicuze mu cyuma","Objet métallique neuf","New metallic object"
                ]
            
        },
        "mwumba": {
            "umuzi/root": "uumba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mwuumba",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mwumba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwanya w'inkoko uba inyuma y'agatorero k'amabuye","Visceres du poussin situés derrière le gésier","Organs of the chick located behind the gizzard"
                ]
            
        },
        "byumba": {
            "umuzi/root": "uumba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "byuumba",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "byumba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru y'urwanda,perefegitura ihana imbibi n'ubuganda","Colline et prefecture de Byumba","Hill and prefecture of Byumba"
                 ]
            
        },
        "urwumbuguru": {
            "umuzi/root": "uumbuguru",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwuumbuguru",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "urwumbuguru",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukwifuza ikintu bikomeye","Forte envie","Strong desire"
                ]
            
        },
        "cyumyarujyo": {
            "umuzi/root": "uumyarujyo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "cyuumyarujyo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "cyumyarujyo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umubeshyi kabuhariwe", "Grand menteur","Big liar"
                ]
            
        },
        "imyuna": {
            "umuzi/root": "uuna",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "imyuuna",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "imyuna",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Amaraso yivusha mu mazuru","Saignement du nez","Nosebleed"
                ]
            
        },
        "icyunamo": {
            "umuzi/root": "uunamo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyuunamo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "icyunamo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Akinjiro umuntu aterwa n'urupfu rw'uwo akunda", "Affliction due au décès d’une pers qu’on aime","mourning"
                ]
            
        },
        "umwunamuko": {
            "umuzi/root": "uunamuko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umwuunamuko",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umwunamuko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Intangiriro y'ahantu hazamuka", "Début d’une montée","Start of an ascent"
                ]
            
        },
        "umunamuko": {
            "umuzi/root": "uunamuko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umuunamuko",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umunamuko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inzuzi zerera umukobwa umuntu ashaka kurongora", "Sorts favorables qui confirment qu’on peut épouser telle jeune fille.","Favorable omens that confirm one can marry such a young girl."
                ]
            
        },
        "rwungeri": {
            "umuzi/root": "uungéri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rwuungéri",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rwungeri",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inyoni y'ikijuju ikunda kuba mu mashinge","Espèce d’oiseau jaune oiseau de la famille des Motacillidae.","Yellow Wagtail, belonging to the family Motacillidae."
                ]
            
        },
        "cyungo": {
            "umuzi/root": "uungo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "cyuungo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "cyungo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bwa perefegitura ya Byumbao","Colline située dans l’ouest de la préfecture de Byumba","Hill located in the west of the Byumba prefecture"
                ]
            
        },
        "urwunguko": {
            "umuzi/root": "uunguko",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "urwuunguko",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "urwunguko",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu cyiyongera ku by'umuntu yari asanzwe atunze", "Intérêt gain surcroît acquisition", "Interest gain surplus acquisition"
                ]
            
        },
        "iyunguruzo": {
            "umuzi/root": "uunguruzo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "iyuunguruzo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "iyunguruzo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ugutera imbere","Progrès","Progress"
                ]
            
        },
        "rwunyura": {
            "umuzi/root": "uunyuura",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "rwuunyuura",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "rwunyura",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igisambo cy'inkengu","Voleur habile","Skillful thief"
                ]
            
        },
        "icyunzwe": {
            "umuzi/root": "uunzwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "icyuunzwe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "icyunzwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubushyuhe bwinshi cyane","Chaleur intense","Intense heat"
                    ]
            
        },
        "ubwururukanzu": {
            "umuzi/root": "uururukanzu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ubwuururukanzu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ubwururukanzu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inzoga bahemba uwasakaye akayinywera aho ngaho","Bière qu’on offre à celui qui a couvert la maison traditionnelle","Beer offered to the one who has thatched the traditional house"
                ]
            
        },
        "ibyusiro": {
            "umuzi/root": "uusiiro",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ibyuusiiro",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ibyusiro",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ibintu by'umurenda byera umugore agenda azana amaze gusama","Pertes blanches d’une femme après la conception", "White discharge from a woman after conception"
                ]
            
        },
        "akuto": {
            "umuzi/root": "uuto",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "akuuto",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "akuto",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Impiswi y'inyamaswa zo mu bwoko bw'ihene n'inkoko","Diarrhée des capridés et de la volaille","Diarrhea in goats and poultry"
                ]
            
        },
        "mvaburayi": {
            "umuzi/root": "vaaburaayi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mvaaburaayi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mvaburayi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Gikomoka mu Burayi","De provenance européenne","Imported from European"
                ]
            
        },
        "mvamahanga": {
            "umuzi/root": "váamahaánga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mváamahaánga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mvamahanga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu cg ikintu gikomoka mu mahanga","importé de l'étranger","imported from foreign"
                ]
            
        },
        "kavengeri": {
            "umuzi/root": "véengeri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kavéengeri",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kavengeri",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu kinini cyane","Chose ou animal très gros", "Thing or animal very large"
                ]
            
        },
        "ruvigira": {
            "umuzi/root": "viigiira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruviigiira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruvigira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umunyagasuzuguro ubwira akigira nk'utakumva","Orgueilleux qui marque du mépris à celui qui lui parle en feignant de ne pas l’entendre.", "Proud person who shows disdain to those who speak to them by pretending not to hear."
                ]
            
        },
        
        "bavukanwa": {
            "umuzi/root": "vuukánwa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "bavuukánwa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "bavukanwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ingeso mbi ya kavukire","Défaut inné","Inherent flaw"
                 ]
            
        },
        "muvumba": {
            "umuzi/root": "vuumba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muvuumba",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muvumba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umugezi wo muri perefegitura ya Byumba bitiriye komini uherereye mo ukisuka mu wa Kagitumba","Rivière située dans la préfecture de Byumba.", "River located in the Byumba prefecture."
                ]
            
        },
        "kivumba": {
            "umuzi/root": "vuumba",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kivuumba",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kivumba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikiyaga kiri muri Pariki y'akagera mu burasirazuba bwa ruguru bwa perefegitura ya Kbungo","Lac situé dans le Parc National de l’Akagera dans le nord","Lake located in Akagera National Park in the north."
                 ]
            
        },
        "buvumo": {
            "umuzi/root": "vumo",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "buvumo",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "buvumo",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burasirazuba bwa komini Gishamvu perefegitura ya Butare","Colline de l’est de la commune Gishamvu dans la préfecture de Butare.","Hill in the east of the Gishamvu commune in the Butare prefecture."
                ]
            
        },
        "ruvumwa": {
            "umuzi/root": "vumwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruvumwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruvumwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu wabaye ruhwitwa bavuga nabi hose kubera imyifatire cg imigenzereze mibi", "Personne détestée de tous à cause de son comportement indigne.","Person hated by all because of their disgraceful behavior"
                ]
        },
        "kivunambavu": {
            "umuzi/root": "vunambavu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kivunambavu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kivunambavu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'igishyimbo","Variété de haricot au goût exquis.","Variety of bean with exquisite taste."
                ]
            
        },
        "ruvundagura": {
            "umuzi/root": "vuundagura",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruvundagura",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruvundagura",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu w'umuswa ukora avundagura","Personne maladroite qui agit avec précipitation", "Clumsy person who acts hastily and without skill"
                ]
            
        },
        "kivunguti": {
            "umuzi/root": "vuunguti",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kivunguti",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kivunguti",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'igishyimbo","Variété de haricot.","Variety of bean."
                ]
            
        },
        "ruvure": {
            "umuzi/root": "vure",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruvure",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruvure",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imbehe nini","Grande ecuelle","Large bowl"
                ]
            
        },
        "mavuta": {
            "umuzi/root": "vuta",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mavuta",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mavuta",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'igishyimbo","Variété de haricot.","Variety of bean."
                ]
            
        },
        "ruyaya": {
            "umuzi/root": "yaáya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruyaáya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruyaya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Utuyuki duke tuva mu muzinga tukigendera","Petit essaim d’abeilles qui quitte une ruche", "Small swarm of bees that leaves a hive"
                ]
            
        },
        "muyenzi": {
            "umuzi/root": "yeenzi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muyeenzi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muyenzi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba inka y'urwirungu rweruruka","Surnom d’une vache de robe gris clair", "Nickname of a light gray cow"
                ]
            
        },
        "kayenzi": {
            "umuzi/root": "yeenzi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kayeenzi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kayenzi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burasirazuba bwa ruguru bwa perefegitura ya Gitarama","Colline et commune situées dans le nord-est de la préfecture Gitarama","Hill and commune located in the north-east of Gitarama prefecture"
                ]
            
        },
        "kayija": {
            "umuzi/root": "yiija",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kayiija",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kayija",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ubwoko bw'insina y'ikakama", "Variété de bananier à bananes amères", "Variety of banana plant with bitter bananas"
                ]
            
        },
        "muyira": {
            "umuzi/root": "yira",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muyira",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muyira",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burasirazuba bwa ruguru bwa perefegitura ya Butare wahaye izina komini urimo","Colline et commune situées dans le nord", "Hill and commune located in the north."
                ]
            
        },
        "inyoberabatutsi": {
            "umuzi/root": "yoberabatuutsi",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "inyoberabatuutsi",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "inyoberabatutsi",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "ubwoko bw'insina","Variété de bananier","banana variety"
                ]
            
        },
        "kwiyoberanya": {
            "umuzi/root": "yoberanya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kwiyoberanya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "cyoberanya",
            "icyiciro/pos": [
                "verb",
                "inshinga"
            ],
            "igisobanuro/meaning": [
                
                    "kwihinduranya kugira batakumenya","disguise","déguiser"
                ]
            
        },
        "buyoga": {
            "umuzi/root": "yogá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "buyogá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "buyoga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bw'amajyepfo bwa perefegitura ya Byumba Wahaye", "Colline située sdu ouest de la préfecture Byumba","Hill located in ouest south of bYumba prefecture"
                ]
        },
        "kiyombe": {
            "umuzi/root": "yoombe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kiyoombe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kiyombe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru ya perefegitura ya Byumba ku mupaka w'ubuganda","Colline et commune situées dans le nord de la préfecture de Byumba limitrophe de l’Ouganda.","A hill and commune located in the northern part of Byumba prefecture, bordering Uganda"
                ]
            
        },
        "umuyonga": {
            "umuzi/root": "yoonga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "umuyoonga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "umuyonga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ivu risigara aho ibintu byinshi byahiriye","Cendres laissées par un grand feu","Ashes left by a great fire"
                ]
            
        },
        "kayonza": {
            "umuzi/root": "yoonzá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kayoonzá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kayonza",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu majyaruguru ya perefegitura ya Kibungo wahaye izina komini uri mo","Colline et commune situées dans le nord de la préfecture de Kibungo.", "Hill and commune located in the north of the Kibungo prefecture."
                ]
            
        },
        "umuyumbu": {
            "umuzi/root": "yuumbu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruyyuumbu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruyumbu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ibara ry'umukara risa n'ubwoya bw'imbogo","Noir ressemblant au pelage du buffle","Black resembling buffalo fur"
                ]
            
        },
        "ruzagayura": {
            "umuzi/root": "zagayura",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruzagayura",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruzagayura",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Inzara yoromeje Urwanda hagati ya 1943 na 1944", "Nom propre de la famine qui a sévi au Rwanda entre 1943 et 1944","Proper name of the famine that struck Rwanda between 1943-1944"
                ]
            
        },
        "muzamba": {
            "umuzi/root": "zaambá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muzzaambá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muzamba",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba umuntu muremure","Surnom donné à une personne de grande taille.", "Nickname given to a tall person."
                ]
            
        },
        "nzambe": {
            "umuzi/root": "zaambé",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nzaambé",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nzambe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Imirimo myinshi itarangira","Occupations pénibles et interminables","Arduous and never-ending tasks"
                ]
            
        },
        "muzana": {
            "umuzi/root": "zaána",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muzzaána",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muzana",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umwe mu baja ba Ryangombe wari ushinzwe imirimo yo mu rugo","Nom d’une des servantes de Ryangombe qui était préposée aux travaux ménagers", "Name of one of the servants of Ryangombe who was in charge of household chores"
                ]
            
        },
        "nzega": {
            "umuzi/root": "zegá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nzegá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nzega",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umusozi wo mu burengerazuba bwa komini Nyamagabe muri perefegitura Gikongoro","Colline située dans la partie orientale de la commune de Nyamagabe dans la préfecture de Gikongoro", "Hill located in the eastern part of the Nyamagabe municipality in the Gikongoro prefecture."
                ]
            
        },
        "ruzerefu": {
            "umuzi/root": "zeréfu",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruzeréfu",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruzerefu",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu bashyira ku ruhande kugira ngo aze gusimbura undi", "Personne qui est de réserve.","Person who is reserved"
                ]
            
        },
        "nzeri": {
            "umuzi/root": "zéri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nzéri",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nzeri",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ukwezi kwa mbere k'umwaka wa kinyarwaanda","Première lunaison de l’année traditionnelle rwandaise","First lunar phase of the traditional Rwandan year"
                ]
            
        },
        "muzigura": {
            "umuzi/root": "ziguura",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muziguura",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muzigura",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                "Umunyampuhwe ukura abandi mu kaga","Personne miséricordieuse qui sauve volontiers les autres du danger","Merciful person who willingly saves others from danger"
                ]
            
        },
        "inzika": {
            "umuzi/root": "zika",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "zika",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "zika",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "umujinya udacogora","lancune","grudge"
                 ]
            
        },
        "buzima": {
            "umuzi/root": "zima",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "buzima",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "buzima",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Igihe cyose umuntu ariho","Aussi longtemps qu’on vit toujours", "As long as one lives always"
                ]
            
        },
        "nzinzingiza": {
            "umuzi/root": "ziingizá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nziinziingizá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nzinzingiza",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu udakoma","Personne silencieuse taciturne", "reserved person."
                ]
            
        },
        "ruzirampuhwe": {
            "umuzi/root": "zirampuhwe",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruzirampuhwe",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruzirampuhwe",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bita umugome utagira imbabazi","Surnom d’un homme méchant et impitoyable", "Nickname of a wicked and ruthless man"
                ]
            
        },
        "kaziri": {
            "umuzi/root": "ziri",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "kaziri",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "kaziri",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu w'umunyamahane cg w'umugome cyane","Personne très querelleuse ou méchante", "Very quarrelsome or mean person"
                ]
            
        },
        "ruzirwa": {
            "umuzi/root": "zirwá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "ruzirwá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "ruzirwa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu gitera ibyago bikomeye cg kirimbura abantu cg ibintu", "Evénement catastrophique","Catastrophic event"
                ]
            
        },
        "muzitsa": {
            "umuzi/root": "zitsa",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muzitsa",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muzitsa",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Kimwe mu bijigo binini bine bimera nyuma y'ibindi byose","Dent de sagesse","Wisdom tooth"
                ]
            
        },
        "mateke": {
            "umuzi/root": "teke",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "máateke",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mateke",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umugore cg umukobwa ufite uburanga bwiza cyane", "Femme ou jeune fille très belle", "Woman or young girl very beautiful"
                ]
            
        },
        "nzobya": {
            "umuzi/root": "zobya",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "nzobya",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "nzobya",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ibere ry'igitoki ry'imfunya riba ku iseri rya nyuma","Banane rabougrie appartenant au dernier segment du régime","Stunted banana belonging to the last segment of the bunch"
                ]        
        },
        "muzuka": {
            "umuzi/root": "zuuka",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muzuuka",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muzuka",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Izina bahimba umuntu uvuye mu byago bikomye","Surnom de celui qui a échappé à un grand danger","Nickname of someone who escaped a great danger"
                ]
            
        },
        "muzunga": {
            "umuzi/root": "zuunga",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "muzuunga",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "muzunga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Ikintu gifata umuntu mu mutwe akagira isesemi akazungurira akenshi akikubita hasi", "Vertige causé par le tournoiement","Dizziness caused by spinning"
                ]
        },
        "mazunga": {
            "umuzi/root": "zuungá",
            "basoma/phonetics": {
                " ": "NA",
                "mu buke/singular": "mazuungá",
                "mu bwinshi/plural": "NA"
            },
            "bandika/writing": "mazunga",
            "icyiciro/pos": [
                "noun",
                "izina"
            ],
            "igisobanuro/meaning": [
                
                    "Umuntu munini kandi muremure","Personne grande et grosse","Large and big person"
                ]
        },
}


def insert_data():
    for word, details in words_data.items():
       #proceed with adding the word to the database
        new_record = WordsData(
            word=word,
            umuzi_root=details["umuzi/root"],
            basoma_phonetics=details["basoma/phonetics"],
            bandika_writing=details["bandika/writing"],
            icyiciro_pos=details["icyiciro/pos"],
            igisobanuro_meaning=details["igisobanuro/meaning"]
        )
        db.session.add(new_record)
    
    db.session.commit()
#Endpoint to look up a word
@app.get("/word/{word_name}")
async def lookup_word(word_name: str, db: Session = Depends(get_db)):
    word_data = db.query(WordsData).filter(WordsData.word == word_name.lower()).first()
    if word_data:
        return {
            "word": word_data.word,
            "umuzi_root": word_data.umuzi_root,
            "basoma_phonetics": word_data.basoma_phonetics,
            "bandika_writing": word_data.bandika_writing,
            "icyiciro_pos": word_data.icyiciro_pos,
            "igisobanuro_meaning": word_data.igisobanuro_meaning
        }
    else:
        raise HTTPException(status_code=404, detail="Word not found")
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session

@app.get("/word/{word_name}/{filter}")
async def lookup_filtered_word(word_name: str, filter: str, db: Session = Depends(get_db)):
    # Convert the word name to lowercase to ensure case-insensitive matching
    word_data = db.query(WordsData).filter(WordsData.word == word_name.lower()).first()
    
    if word_data:
        # Define a dictionary mapping the filter to the appropriate field in WordsData
        filter_mapping = {
            "root": word_data.umuzi_root,
            "phonetics": word_data.basoma_phonetics,
            "writing": word_data.bandika_writing,
            "pos": word_data.icyiciro_pos,
            "meaning": word_data.igisobanuro_meaning
           
        }
        
        # Check if the filter exists in the mapping
        if filter in filter_mapping:
            return {filter: filter_mapping[filter]}
        else:
            raise HTTPException(status_code=400, detail="Invalid filter field")
    else:
        raise HTTPException(status_code=404, detail="Word not found")



