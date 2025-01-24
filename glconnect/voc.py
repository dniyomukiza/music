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
            [
                "Ahantu hafunganye","Lieu exigu","confined space"
            ]
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
            [
                "Gushyira umuntu cg ikintu ahaga","Pousser mettre à l’étroit ou serrer les uns contre les autres","To push, squeeze, or press things or people tightly together"
            ]
            
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
            [
                "umutego w'imbeba","piège à souris","mouse trap"
            ]
            
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
            [
                "Gutumbagana kw'umuntu cg ikintu kikuzuriza","Enfler se dilater très fort","Swelling, expanding very strongly"
            ]
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



