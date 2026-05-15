working sections in bootstrap:
disassembly
cleaning
structural repair
sanding
upholstery removal
padding
upholstery installation
assembly
sewing
weaving

it should have the image in the creation but for now we will pass an empty string


for dependencies: 
dissasembly has no dependencies

cleaning depends on disassembly

structural repair depends on disassembly

sanding depends on structural repair 

upholstery removal depends on dissasembly 

padding depends on upholstery removal

upholstery installation depends on padding and upholstery removal

assembly depends on upholstery installation, structural repair, and sanding

sweing depends on dissasembly, upholstery removal

weaving depends on sewing




Issues in bootstrap:

scratches
dents
broken parts
stains
structural damage
finish damage
assembly issues
loose joints
upholstery damage


issues severity:
low - 1.1
medium - 1.5
high - 2.0


issue categories config in bootstrap:

for working section "structural repair", sanding:
scratches - to all item categories with major_category of seating 
dents - to all item categories with major_category of seating
broken parts - to all item categories with major_category of seating
stains - to all item categories with major_category of seating
structural damage - to all item categories with major_category of seating
finish damage - to all item categories with major_category of seating
loose joints - to all item categories with major_category of seating




for working section "upholstery installation", "sewing", "weaving":
upholstery damage - to all item categories with major_category of seating




for working section "assembly":

assembly issues - to all item categories with major_category of seating

loose joints - to all item categories with major_category of seating


base time can be places as 10 minutes for all


item categories in bootstrap:

two major categories: seating and wood.

seating has the following categories:  "armchair",

    "bench",

    "chair",

    "chairs",

    "dining chair",

    "sofa",

    "stool",

wood has the following categories: "bar cabinet",

    "bedside table",

    "bookshelf",

    "cabinet",

    "chest of drawer",

    "chest of drawers",

    "coffee table",

    "conference table",

    "corner cabinet",

    "dining table",

    "hall table",

    "highboard",

    "lamp",

    "mirror",

    "nest of tables",

    "plant stand",

    "poster",

    "round table",

    "secretary",

    "serving trolley",

    "side table",

    "sideboard",

    "small table",

    "shelving",

    "sewing table",

    "trolley",

    "writing desk",
