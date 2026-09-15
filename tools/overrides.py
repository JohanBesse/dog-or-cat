"""
Better Commons photos than the ones Wikipedia leads with.

`prop=pageimages` returns whatever image sits at the top of the article, which
for a handful of species is the wrong picture to play with: too small for the
layout -- the African civet's is 500 pixels wide -- or a close-up of a nose, or
a montage rather than a photograph. Commons almost always holds a better photo
of the same animal, so those species are pinned to a file by hand here.

Keys are Wikipedia article titles, exactly as they appear in SPECIES; values
are Commons filenames without the "File:" prefix. Anything listed here skips
the pageimages lookup and goes straight to imageinfo, so the licence and the
photographer are still read from Commons rather than assumed.

Every entry was looked at before being added. The build warns about any source
narrower than 1280 px and refuses to ship one narrower than 660.
"""

OVERRIDES = {
    # article lead is 500x?? -- a dark, cropped face
    "African_civet":
        "African civet, South Luangwa National Park (51866143791).jpg",
    # article lead is 563x565
    "Polar_bear":
        "Polar Bear with its tongue sticking out.jpg",
    # article lead is 576 wide, dark and behind wire
    "Kinkajou":
        "Selva verde lodge pm 4.18.25 DSC 3210-topaz-rawdenoise.jpg",
    # article lead is 600 wide
    "Sand_cat":
        "Arabian Sand Cat - Felis Margarita.jpg",

    # The next two are not about size. Wikipedia's lead image is a poor
    # photograph to guess from, which for this game is the same problem.

    # the article leads with "Banded_Mongoose_Nose_Detail,_crop.jpg", which is
    # a close-up of a nose: the bands it is named after are not even in shot
    "Banded_mongoose":
        "Banded mongoose (Mungos mungo).jpg",
    # the article leads with a two-photo montage rather than a photograph
    "Raccoon_dog":
        "Єнотовидний собака (Nyctereutes procyonoides).jpg",
}
