import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, HTTPException, Depends
from dotenv import load_dotenv
from glconnect.models import WordsData,db
from sqlalchemy.orm import declarative_base


# Load environment variables
load_dotenv()
db_url = os.getenv('DB_URL')  # Make sure to set this in your environment or config

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

}


def insert_data():
    for word, details in words_data.items():
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



