import json
import logging
from backend.database.db import get_db_connection, init_db
from backend.services.faiss_service import faiss_service

logger = logging.getLogger("daic.seed")

DEMO_DOCUMENTS = [
    {
        "id": "BAWS_VOL_10_LABOUR",
        "title": "Dr. Babasaheb Ambedkar: Writings and Speeches, Vol. 10",
        "type": "Book",
        "year": 1942,
        "date_str": "1942–1946",
        "collection": "Writings and Speeches",
        "author": "Dr. B. R. Ambedkar",
        "language": "en",
        "source_institution": "Dr. Ambedkar Foundation, Ministry of Social Justice & Empowerment",
        "source_url": "https://ambedkarfoundation.nic.in/writings-and-speeches",
        "page_count": 560,
        "digitization_method": "Institutional Flatbed Archival Scanner (600 DPI)",
        "ocr_status": "archivist_reviewed",
        "verification_status": "DEMO DATA",
        "provenance_type": "DEMO DATA",
        "summary": "Official proceedings, speeches, and legislative measures of Dr. B. R. Ambedkar as Member for Labour in the Viceroy's Executive Council (1942–1946), establishing fundamental labour rights, reducing daily work hours from 12 to 8, instituting the Coal Mines Safety Stowing Act, maternity benefits, and the Employment Exchange network in India.",
        "chunks": [
            {
                "id": "BAWS_V10_C01",
                "page": 85,
                "section_title": "Reduction of Working Hours & Social Security",
                "content": "At the 7th session of the Indian Labour Conference held in New Delhi on 27 November 1942, Dr. B. R. Ambedkar as the Labour Member moved the resolution to reduce daily factory working hours from 12 hours to 8 hours. He emphasized that labour legislation is not a concession but an inherent social right essential for human dignity and democratic citizenship. The conference established statutory tripartite consultations among labour representatives, employers, and government.",
            },
            {
                "id": "BAWS_V10_C02",
                "page": 112,
                "section_title": "Tripartite Labour Machinery & Democratic Participation",
                "content": "In his opening address to the Standing Labour Committee on 30 November 1942, Ambedkar articulated the imperative of establishing statutory tripartite machinery. He stated that peace in industry cannot be maintained by repression, but through democratic consultation, fair wage standards, social security insurance, and the statutory recognition of trade unions across all industrial sectors.",
            },
            {
                "id": "BAWS_V10_C03",
                "page": 198,
                "section_title": "Maternity Benefits & Women Labour Protections",
                "content": "Addressing the Central Legislative Assembly on the Mines Maternity Benefit (Amendment) Bill in 1943, Ambedkar stated that equal protection of female industrial workers, including paid maternity leave and prohibition of underground employment of women in coal mines, was a primary responsibility of the State. He linked women's economic independence directly to social progress.",
            }
        ]
    },
    {
        "id": "BAWS_VOL_05_PROVIDENCE",
        "title": "Dr. Babasaheb Ambedkar: Writings and Speeches, Vol. 5",
        "type": "Book",
        "year": 1945,
        "date_str": "1945",
        "collection": "Writings and Speeches",
        "author": "Dr. B. R. Ambedkar",
        "language": "en",
        "source_institution": "Dr. Ambedkar Foundation, Ministry of Social Justice & Empowerment",
        "source_url": "https://ambedkarfoundation.nic.in/writings-and-speeches",
        "page_count": 482,
        "digitization_method": "High-Resolution Dual-Lens Overhead Capture",
        "ocr_status": "archivist_reviewed",
        "verification_status": "DEMO DATA",
        "provenance_type": "DEMO DATA",
        "summary": "Critical archival examination of socio-political conditions, civil liberties, and the structural emancipation of depressed classes in pre-independence India.",
        "chunks": [
            {
                "id": "BAWS_V05_C01",
                "page": 307,
                "section_title": "Under the Providence of Mr. Gandhi",
                "content": "In Volume 5, page 307, under the section 'Under the Providence of Mr. Gandhi', the archival record documents Ambedkar's rigorous sociological critique of paternalistic reformism versus constitutional rights. He maintained that civic rights, equal access to civic amenities, and political representation must be grounded in statutory constitutional guarantees rather than philanthropic goodwill.",
            },
            {
                "id": "BAWS_V05_C02",
                "page": 308,
                "section_title": "Constitutional Guarantees for Civic Equality",
                "content": "Continuing on pages 307–308 of Volume 5, Ambedkar demonstrated that social democracy cannot exist without structural safeguards against caste discrimination. He documented specific cases where customary village sanctions denied fundamental rights, arguing that the law must actively penalize discrimination in public utilities, water sources, and educational institutions.",
            }
        ]
    },
    {
        "id": "CAD_VOL_07_ART17",
        "title": "Constituent Assembly Debates, Vol. VII",
        "type": "Constitutional Debate",
        "year": 1948,
        "date_str": "29 November 1948",
        "collection": "Constituent Assembly Debates Archive",
        "author": "Dr. B. R. Ambedkar & Drafting Committee",
        "language": "en",
        "source_institution": "Parliament Library of India & National Digital Library of India",
        "source_url": "https://eparlib.nic.in",
        "page_count": 820,
        "digitization_method": "Parliamentary Digitization Project (Microfilm to TIFF)",
        "ocr_status": "archivist_reviewed",
        "verification_status": "DEMO DATA",
        "provenance_type": "DEMO DATA",
        "summary": "Official verbatim records of the Constituent Assembly of India debating Draft Article 11 (which became Article 17 of the Constitution of India), abolishing 'Untouchability' and forbidding its practice in any form.",
        "chunks": [
            {
                "id": "CAD_V07_C01",
                "page": 653,
                "section_title": "Debate on Draft Article 11 (Article 17 - Abolition of Untouchability)",
                "content": "On 29 November 1948, the Constituent Assembly considered Draft Article 11: '\"Untouchability\" is abolished and its practice in any form is forbidden. The enforcement of any disability arising out of \"Untouchability\" shall be an offence punishable in accordance with law.' Dr. B. R. Ambedkar as Chairman of the Drafting Committee oversaw the passage of this foundational human rights clause without dissent, establishing non-discrimination as an enforceable constitutional command.",
            },
            {
                "id": "CAD_V07_C02",
                "page": 655,
                "section_title": "Penal Enforcement and Fundamental Freedom",
                "content": "The Assembly proceedings record that members recognized the historic significance of Draft Article 11 as a charter of human liberation. Dr. Ambedkar ensured that the provision did not merely declare an abstract moral principle, but explicitly commanded Parliament to make its enforcement an offense punishable by penal law, subsequently embodied in the Protection of Civil Rights Act.",
            }
        ]
    },
    {
        "id": "CAD_FINAL_SPEECH_1949",
        "title": "Closing Address to the Constituent Assembly: Social Democracy",
        "type": "Speech",
        "year": 1949,
        "date_str": "25 November 1949",
        "collection": "Constituent Assembly Debates Archive",
        "author": "Dr. B. R. Ambedkar",
        "language": "en",
        "source_institution": "Parliament Library of India",
        "source_url": "https://eparlib.nic.in",
        "page_count": 24,
        "digitization_method": "Official Hansard Transcription & Audio Archive",
        "ocr_status": "verified",
        "verification_status": "DEMO DATA",
        "provenance_type": "DEMO DATA",
        "summary": "Dr. B. R. Ambedkar's final speech in the Constituent Assembly on 25 November 1949, introducing the adoption of the Constitution of India and warning against the perils of maintaining social and economic inequalities alongside political democracy.",
        "chunks": [
            {
                "id": "CAD_FIN_C01",
                "page": 12,
                "section_title": "Definition of Social Democracy & Political Democracy",
                "content": "In his historic closing address on 25 November 1949, Dr. Ambedkar defined social democracy: 'Political democracy cannot last unless there lies at the base of it social democracy. What does social democracy mean? It means a way of life which recognizes liberty, equality and fraternity as the principles of life.' He emphasized that these principles form an inseparable trinity: without equality, liberty produces supremacy of the few; without liberty, equality suffocates individual initiative.",
            },
            {
                "id": "CAD_FIN_C02",
                "page": 15,
                "section_title": "Entering a Life of Contradictions",
                "content": "Ambedkar cautioned the emerging republic: 'On the 26th of January 1950, we are going to enter into a life of contradictions. In politics we will have equality and in social and economic life we will have inequality. In politics we will be recognizing the principle of one man one vote and one vote one value. In our social and economic life, we shall, by reason of our social and economic structure, continue to deny the principle of one man one value.'",
            }
        ]
    },
    {
        "id": "MAHAD_SATYAGRAHA_1927",
        "title": "Declaration of the Mahad Satyagraha and Chavdar Tale Conference",
        "type": "Manuscript",
        "year": 1927,
        "date_str": "19–20 March 1927",
        "collection": "Historical Records & Manuscripts",
        "author": "Dr. B. R. Ambedkar & Bahishkrit Hitakarini Sabha",
        "language": "en",
        "source_institution": "Maharashtra State Archives & Dr. Ambedkar Memorial Society",
        "source_url": "https://archives.maharashtra.gov.in",
        "page_count": 18,
        "digitization_method": "High-Definition Multispectral Facsimile",
        "ocr_status": "archivist_reviewed",
        "verification_status": "DEMO DATA",
        "provenance_type": "DEMO DATA",
        "summary": "Archival declaration and resolutions of the Mahad Satyagraha at the Chavdar Tale (water reservoir), establishing the civil right of depressed classes to public civic resources.",
        "chunks": [
            {
                "id": "MAHAD_C01",
                "page": 4,
                "section_title": "Asserting Human Equality at Chavdar Tale",
                "content": "At the Mahad conference on 20 March 1927, Dr. Ambedkar led thousands of delegates to the Chavdar water tank to drink water from the public reservoir. In his address, he affirmed: 'We are not going to the Chavdar Tank merely to drink water. We are going to the tank to assert that we too are human beings like others.' The movement marked the decisive transformation of the struggle from passive petitions to direct civic assertion of fundamental human rights.",
            }
        ]
    }
]

TIMELINE_SEED = [
    {
        "id": "EVT_1891",
        "year": 1891,
        "date_str": "14 April 1891",
        "title": "Birth of Bhimrao Ramji Ambedkar",
        "category": "Life",
        "description": "Born in Mhow (now Dr. Ambedkar Nagar), Central Provinces, as the fourteenth child of Ramji Sakpal and Bhimbai Murbadkar.",
        "related_documents": json.dumps(["BAWS_VOL_10_LABOUR"]),
        "related_people": json.dumps(["Ramji Sakpal", "Bhimbai Murbadkar"]),
        "related_media": json.dumps(["MED_01"]),
        "quote": "Educate, Agitate, Organise."
    },
    {
        "id": "EVT_1916",
        "year": 1916,
        "date_str": "9 May 1916",
        "title": "Castes in India Paper at Columbia University",
        "category": "Education",
        "description": "Presented groundbreaking anthropological research paper 'Castes in India: Their Mechanism, Genesis and Development' at Columbia University anthropology seminar presided by Dr. Alexander Goldenweiser.",
        "related_documents": json.dumps(["BAWS_VOL_05_PROVIDENCE"]),
        "related_people": json.dumps(["Prof. John Dewey", "Alexander Goldenweiser"]),
        "related_media": json.dumps([]),
        "quote": "Caste is an enclosed class."
    },
    {
        "id": "EVT_1927",
        "year": 1927,
        "date_str": "20 March 1927",
        "title": "Mahad Satyagraha (Chavdar Tale)",
        "category": "Social movements",
        "description": "Historic civil rights assertion at Mahad, Maharashtra, asserting equal access to public water resources and human dignity.",
        "related_documents": json.dumps(["MAHAD_SATYAGRAHA_1927"]),
        "related_people": json.dumps(["Dr. B. R. Ambedkar"]),
        "related_media": json.dumps(["MED_02"]),
        "quote": "We are going to the tank to assert that we too are human beings."
    },
    {
        "id": "EVT_1930",
        "year": 1930,
        "date_str": "2 March 1930",
        "title": "Kalaram Temple Entry Satyagraha",
        "category": "Social movements",
        "description": "Initiated non-violent civil rights demonstration demanding temple entry in Nashik, asserting complete social and religious equality.",
        "related_documents": json.dumps(["BAWS_VOL_05_PROVIDENCE"]),
        "related_people": json.dumps(["Dr. B. R. Ambedkar", "Bhaurao Gaikwad"]),
        "related_media": json.dumps([]),
        "quote": "Self-respect is the most vital factor in life."
    },
    {
        "id": "EVT_1942",
        "year": 1942,
        "date_str": "20 July 1942",
        "title": "Appointed Labour Member of Viceroy's Council",
        "category": "Economics",
        "description": "Appointed to Viceroy's Executive Council. Instituted 8-hour workday, Employees' State Insurance, coal mine safety, and national employment exchanges.",
        "related_documents": json.dumps(["BAWS_VOL_10_LABOUR"]),
        "related_people": json.dumps(["Dr. B. R. Ambedkar"]),
        "related_media": json.dumps(["MED_03"]),
        "quote": "Labour legislation is not a concession, but an inherent social right."
    },
    {
        "id": "EVT_1947",
        "year": 1947,
        "date_str": "29 August 1947",
        "title": "Appointed Chairman of the Drafting Committee",
        "category": "Constitution",
        "description": "Elected Chairman of the Drafting Committee of the Constituent Assembly to frame the Constitution of independent India.",
        "related_documents": json.dumps(["CAD_VOL_07_ART17", "CAD_FINAL_SPEECH_1949"]),
        "related_people": json.dumps(["Dr. B. R. Ambedkar", "Alladi Krishnaswami Ayyar", "K. M. Munshi", "B. N. Rau"]),
        "related_media": json.dumps(["MED_04"]),
        "quote": "Constitutional morality is not a natural sentiment. It has to be cultivated."
    },
    {
        "id": "EVT_1948",
        "year": 1948,
        "date_str": "29 November 1948",
        "title": "Abolition of Untouchability (Article 17 Adopted)",
        "category": "Constitution",
        "description": "Draft Article 11 unanimously adopted by the Constituent Assembly, declaring untouchability abolished and its practice punishable by law.",
        "related_documents": json.dumps(["CAD_VOL_07_ART17"]),
        "related_people": json.dumps(["Dr. B. R. Ambedkar"]),
        "related_media": json.dumps([]),
        "quote": "Untouchability is abolished and its practice in any form is forbidden."
    },
    {
        "id": "EVT_1950",
        "year": 1950,
        "date_str": "26 January 1950",
        "title": "Constitution of India Comes into Force",
        "category": "Constitution",
        "description": "The Republic of India is established as the world's largest constitutional democracy based on justice, liberty, equality, and fraternity.",
        "related_documents": json.dumps(["CAD_FINAL_SPEECH_1949"]),
        "related_people": json.dumps(["Dr. B. R. Ambedkar", "Dr. Rajendra Prasad"]),
        "related_media": json.dumps(["MED_04"]),
        "quote": "However good a Constitution may be, it is sure to turn out bad if those who are called upon to work it happen to be a bad lot."
    },
    {
        "id": "EVT_1956",
        "year": 1956,
        "date_str": "14 October 1956",
        "title": "Deekshabhoomi Dhamma Deeksha in Nagpur",
        "category": "Life",
        "description": "Embraced Buddhism along with over 500,000 followers at Deekshabhoomi, Nagpur, initiating the Buddhist revival movement in modern India.",
        "related_documents": json.dumps(["BAWS_VOL_05_PROVIDENCE"]),
        "related_people": json.dumps(["Dr. B. R. Ambedkar", "Dr. Savita Ambedkar"]),
        "related_media": json.dumps(["MED_05"]),
        "quote": "I like the religion that teaches liberty, equality and fraternity."
    }
]

KNOWLEDGE_ENTITIES = [
    {"id": "ENT_AMBEDKAR", "label": "Dr. B. R. Ambedkar", "category": "Person", "description": "Jurist, economist, social reformer, Chairman of the Constitution Drafting Committee, and Minister of Law and Labour.", "document_id": "CAD_FINAL_SPEECH_1949"},
    {"id": "ENT_CONSTITUENT_ASSEMBLY", "label": "Constituent Assembly", "category": "Institution", "description": "Sovereign body elected to draft the Constitution of India (1946–1950).", "document_id": "CAD_VOL_07_ART17"},
    {"id": "ENT_ARTICLE_17", "label": "Article 17 (Abolition of Untouchability)", "category": "Idea", "description": "Fundamental right abolishing untouchability and criminalizing disability enforcement.", "document_id": "CAD_VOL_07_ART17"},
    {"id": "ENT_SOCIAL_DEMOCRACY", "label": "Social Democracy", "category": "Idea", "description": "Concept of democracy as a way of life based on an inseparable trinity of liberty, equality, and fraternity.", "document_id": "CAD_FINAL_SPEECH_1949"},
    {"id": "ENT_LABOUR_RIGHTS", "label": "Labour Rights & 8-Hour Workday", "category": "Idea", "description": "Statutory reduction of working hours from 12 to 8, maternity benefits, tripartite consultation, and employment exchanges.", "document_id": "BAWS_VOL_10_LABOUR"},
    {"id": "ENT_MAHAD_SATYAGRAHA", "label": "Mahad Satyagraha", "category": "Event", "description": "Historic civil rights assertion at Chavdar Tale on 20 March 1927 for equal access to civic water resources.", "document_id": "MAHAD_SATYAGRAHA_1927"},
    {"id": "ENT_WRITINGS_SPEECHES", "label": "Writings & Speeches", "category": "Document", "description": "Official institutional archival corpus published by Dr. Ambedkar Foundation.", "document_id": "BAWS_VOL_10_LABOUR"},
    {"id": "ENT_POONA_PACT", "label": "Poona Pact (1932)", "category": "Event", "description": "Agreement establishing reserved legislative seats for Depressed Classes within the general electorate.", "document_id": "BAWS_VOL_05_PROVIDENCE"},
    {"id": "ENT_HINDU_CODE_BILL", "label": "Hindu Code Bill", "category": "Document", "description": "Legislative reform guaranteeing women's inheritance rights, monogamy, and divorce rights.", "document_id": "CAD_FINAL_SPEECH_1949"},
    {"id": "ENT_COLUMBIA_UNIVERSITY", "label": "Columbia University", "category": "Place", "description": "Institution where Ambedkar earned M.A. and Ph.D. under John Dewey and Edwin Seligman.", "document_id": "BAWS_VOL_05_PROVIDENCE"}
]

KNOWLEDGE_RELATIONS = [
    {"id": "REL_01", "source_id": "ENT_AMBEDKAR", "target_id": "ENT_CONSTITUENT_ASSEMBLY", "relation": "Chaired Drafting Committee of", "description": "Dr. Ambedkar was elected Chairman of the Drafting Committee on 29 August 1947.", "citation_id": "CAD_VOL_07_ART17"},
    {"id": "REL_02", "source_id": "ENT_AMBEDKAR", "target_id": "ENT_ARTICLE_17", "relation": "Drafted and steered", "description": "Draft Article 11 was shepherded by Ambedkar to unanimous constitutional passage.", "citation_id": "CAD_VOL_07_ART17"},
    {"id": "REL_03", "source_id": "ENT_AMBEDKAR", "target_id": "ENT_SOCIAL_DEMOCRACY", "relation": "Articulated philosophy of", "description": "Defined social democracy in his final Constituent Assembly address on 25 Nov 1949.", "citation_id": "CAD_FINAL_SPEECH_1949"},
    {"id": "REL_04", "source_id": "ENT_AMBEDKAR", "target_id": "ENT_LABOUR_RIGHTS", "relation": "Enacted as Labour Member", "description": "Instituted 8-hour workday, maternity benefits, and tripartite labor machinery 1942–46.", "citation_id": "BAWS_VOL_10_LABOUR"},
    {"id": "REL_05", "source_id": "ENT_AMBEDKAR", "target_id": "ENT_MAHAD_SATYAGRAHA", "relation": "Led and proclaimed", "description": "Led thousands to Chavdar Tale in March 1927 proclaiming human equality.", "citation_id": "MAHAD_SATYAGRAHA_1927"},
    {"id": "REL_06", "source_id": "ENT_AMBEDKAR", "target_id": "ENT_WRITINGS_SPEECHES", "relation": "Authored comprehensive corpus", "description": "Preserved across institutional volumes published by Dr. Ambedkar Foundation.", "citation_id": "BAWS_VOL_10_LABOUR"},
    {"id": "REL_07", "source_id": "ENT_CONSTITUENT_ASSEMBLY", "target_id": "ENT_ARTICLE_17", "relation": "Adopted into Constitution", "description": "Adopted on 29 November 1948.", "citation_id": "CAD_VOL_07_ART17"},
    {"id": "REL_08", "source_id": "ENT_AMBEDKAR", "target_id": "ENT_COLUMBIA_UNIVERSITY", "relation": "Alumnus (Ph.D. Economics)", "description": "Awarded M.A. in 1915 and Ph.D. in 1917.", "citation_id": "BAWS_VOL_05_PROVIDENCE"}
]

MEDIA_SEED = [
    {
        "id": "MED_01",
        "title": "Dr. B. R. Ambedkar addressing Constituent Assembly",
        "type": "photo",
        "date": "25 November 1949",
        "duration": "Archival Still",
        "collection": "Parliament of India Photographic Archives",
        "description": "Historical photograph of Dr. B. R. Ambedkar presenting the final draft of the Constitution in the Central Hall of Parliament.",
        "thumbnail_url": "/assets/media_ambedkar_cad.jpg",
        "media_url": "/assets/media_ambedkar_cad.jpg",
        "transcript": "Visual record of Dr. Ambedkar standing before the podium in Central Hall, New Delhi.",
        "audio_narration_text": "Archival still record: Dr. Babasaheb Ambedkar addressing the final session of the Constituent Assembly of India on November 25, 1949."
    },
    {
        "id": "MED_02",
        "title": "Mahad Satyagraha Commemoration Speech (Audio Recording)",
        "type": "audio",
        "date": "20 March 1927",
        "duration": "03:45",
        "collection": "All India Radio Archival Transcriptions",
        "description": "Historical narration and reading of the Chavdar Tale Declaration of Human Rights.",
        "thumbnail_url": "/assets/media_mahad.jpg",
        "media_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/A_speech_by_Ambedkar.ogg",
        "transcript": "We are going to the Chavdar Tank to assert that we too are human beings like others...",
        "audio_narration_text": "Listen to the historical declaration of the Mahad Satyagraha, wherein Dr. Ambedkar asserted civic equality at the Chavdar water reservoir."
    },
    {
        "id": "MED_03",
        "title": "Tripartite Labour Conference Proceedings (1942)",
        "type": "documentary",
        "date": "27 November 1942",
        "duration": "05:12",
        "collection": "Labour Archives of India (V. V. Giri National Labour Institute)",
        "description": "Institutional archival overview of the 7th Indian Labour Conference where the 8-hour workday was codified.",
        "thumbnail_url": "/assets/media_labour.jpg",
        "media_url": "/assets/media_labour.mp4",
        "transcript": "Proceedings of the Labour Member of the Viceroy's Executive Council formulating statutory working hour reforms.",
        "audio_narration_text": "Archival documentary recording the landmark 1942 tripartite conference establishing the eight hour work day in India."
    }
]

STORIES_SEED = [
    {
        "id": "STORY_CONSTITUTION",
        "slug": "making-of-the-constitution",
        "title": "The Making of the Constitution: Drafting a Charter of Liberty",
        "subtitle": "How Dr. B. R. Ambedkar and the Drafting Committee forged the world's most comprehensive constitutional democracy.",
        "cover_image": "/assets/story_constitution.jpg",
        "excerpt": "Explore the deliberations, contentious debates, and foundational principles that shaped the Constitution of India between 1946 and 1950.",
        "timeline_year": "1946–1950",
        "content_json": json.dumps([
            {
                "heading": "The Mandate of the Drafting Committee",
                "text": "On 29 August 1947, the Constituent Assembly appointed a Drafting Committee presided over by Dr. B. R. Ambedkar. Tasked with synthesising human rights, parliamentary democracy, and social justice, Ambedkar brought unparalleled comparative constitutional expertise.",
                "citation": "CAD Vol. VII, Page 653"
            },
            {
                "heading": "Abolition of Untouchability as a Fundamental Right",
                "text": "The passage of Draft Article 11 (Article 17) represented a watershed in global constitutionalism: an explicit constitutional decree criminalizing caste discrimination and disabilities in any form.",
                "citation": "CAD Vol. VII, Debate on Draft Article 11"
            },
            {
                "heading": "The Inseparable Trinity of Social Democracy",
                "text": "In his final address on 25 November 1949, Ambedkar insisted that political democracy (one person, one vote) must be complemented by social and economic democracy (one person, one value), declaring liberty, equality, and fraternity as the nation's guiding compass.",
                "citation": "Constituent Assembly Debates, 25 Nov 1949, p. 12"
            }
        ]),
        "sources_json": json.dumps(["CAD_VOL_07_ART17", "CAD_FINAL_SPEECH_1949"])
    },
    {
        "id": "STORY_MAHAD",
        "slug": "the-mahad-satyagraha",
        "title": "The Mahad Satyagraha: Awakening of Human Dignity",
        "subtitle": "The 1927 civil rights watershed that redefined social justice in modern India.",
        "cover_image": "/assets/story_mahad.jpg",
        "excerpt": "At the Chavdar water tank in Mahad, Dr. Ambedkar led the assertion of human rights that declared access to water as a fundamental civic right.",
        "timeline_year": "1927",
        "content_json": json.dumps([
            {
                "heading": "The Call at Chavdar Tale",
                "text": "On 20 March 1927, thousands of delegates assembled under the auspices of the Bahishkrit Hitakarini Sabha marched peacefully to the Chavdar water reservoir in Mahad.",
                "citation": "Mahad Satyagraha Archival Declaration, p. 4"
            },
            {
                "heading": "Water as a Symbol of Human Dignity",
                "text": "Drinking from the public tank was not merely an act of quenching thirst, but a historic assertion that caste-based exclusions violated elementary human dignity.",
                "citation": "Maharashtra State Archives Record 1927"
            }
        ]),
        "sources_json": json.dumps(["MAHAD_SATYAGRAHA_1927"])
    },
    {
        "id": "STORY_LABOUR",
        "slug": "ambedkar-and-labour-rights",
        "title": "Dr. Ambedkar and Labour Rights: Architect of Modern Work Standards",
        "subtitle": "How the 8-hour workday, maternity benefits, and social security were codified into Indian law.",
        "cover_image": "/assets/story_labour.jpg",
        "excerpt": "As Labour Member of the Viceroy's Executive Council (1942–1946), Dr. Ambedkar transformed labour from exploitation to statutory constitutional protection.",
        "timeline_year": "1942–1946",
        "content_json": json.dumps([
            {
                "heading": "Reduction to the 8-Hour Workday",
                "text": "Prior to 1942, factory labourers in India toiled up to 12 to 14 hours daily. Ambedkar moved the resolution at the 7th Indian Labour Conference reducing working hours to 8 hours.",
                "citation": "BAWS Vol. 10, Page 85"
            },
            {
                "heading": "Maternity Benefits and Equal Protections",
                "text": "Ambedkar pioneered the Mines Maternity Benefit Bill and the Employment Exchanges network, ensuring that women received paid maternity benefits and workplace protections.",
                "citation": "BAWS Vol. 10, Page 198"
            }
        ]),
        "sources_json": json.dumps(["BAWS_VOL_10_LABOUR"])
    }
]

def seed_database():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing demo seed records if present
    cursor.execute("DELETE FROM chunks WHERE provenance_type = 'DEMO DATA';")
    cursor.execute("DELETE FROM documents WHERE provenance_type = 'DEMO DATA';")
    cursor.execute("DELETE FROM archive_fts;")
    cursor.execute("DELETE FROM timeline_events WHERE provenance_type = 'DEMO DATA';")
    cursor.execute("DELETE FROM knowledge_entities WHERE provenance_type = 'DEMO DATA';")
    cursor.execute("DELETE FROM knowledge_relations;")
    cursor.execute("DELETE FROM media WHERE provenance_type = 'DEMO DATA';")
    cursor.execute("DELETE FROM stories WHERE provenance_type = 'DEMO DATA';")

    all_chunks_for_faiss = []

    # Insert Documents & Chunks
    for doc in DEMO_DOCUMENTS:
        cursor.execute("""
            INSERT OR REPLACE INTO documents (
                id, title, type, year, date_str, collection, author, language,
                source_institution, source_url, page_count, digitization_method,
                ocr_status, verification_status, provenance_type, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc["id"], doc["title"], doc["type"], doc["year"], doc["date_str"],
            doc["collection"], doc["author"], doc["language"], doc["source_institution"],
            doc["source_url"], doc["page_count"], doc["digitization_method"],
            doc["ocr_status"], doc["verification_status"], doc["provenance_type"], doc["summary"]
        ))

        for chunk in doc["chunks"]:
            cursor.execute("""
                INSERT OR REPLACE INTO chunks (
                    id, document_id, chunk_index, page, section_title, content,
                    char_count, word_count, provenance_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk["id"], doc["id"], 1, chunk["page"], chunk["section_title"],
                chunk["content"], len(chunk["content"]), len(chunk["content"].split()),
                doc["provenance_type"]
            ))

            # Insert into SQLite FTS5 table
            cursor.execute("""
                INSERT INTO archive_fts (chunk_id, document_id, title, content, collection, author, section_title)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk["id"], doc["id"], doc["title"], chunk["content"],
                doc["collection"], doc["author"], chunk["section_title"]
            ))

            all_chunks_for_faiss.append({
                "chunk_id": chunk["id"],
                "document_id": doc["id"],
                "page": chunk["page"],
                "section_title": chunk["section_title"],
                "title": doc["title"],
                "collection": doc["collection"],
                "author": doc["author"],
                "content": chunk["content"],
                "provenance_type": doc["provenance_type"]
            })

    # Also preserve & re-index any existing non-demo verified chunks in SQLite into FTS5 and FAISS
    cursor.execute("""
        SELECT c.id, c.document_id, c.page, c.section_title, c.content, c.provenance_type,
               d.title, d.collection, d.author, d.verification_status, d.provenance_type AS doc_prov
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.provenance_type != 'DEMO DATA' AND d.verification_status = 'VERIFIED SOURCE'
    """)
    non_demo_verified = cursor.fetchall()
    for row in non_demo_verified:
        cursor.execute("""
            INSERT INTO archive_fts (chunk_id, document_id, title, content, collection, author, section_title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            row["id"], row["document_id"], row["title"], row["content"],
            row["collection"], row["author"], row["section_title"]
        ))
        prov = row["provenance_type"] if row["provenance_type"] not in ("VERIFIED SOURCE", None) else (row["doc_prov"] or "USER-UPLOADED DATA")
        all_chunks_for_faiss.append({
            "chunk_id": row["id"],
            "document_id": row["document_id"],
            "page": row["page"],
            "section_title": row["section_title"] or "",
            "title": row["title"] or "",
            "collection": row["collection"] or "",
            "author": row["author"] or "",
            "content": row["content"],
            "provenance_type": prov,
            "verification_status": "VERIFIED SOURCE"
        })

    # Insert Timeline
    for evt in TIMELINE_SEED:
        cursor.execute("""
            INSERT OR REPLACE INTO timeline_events (
                id, year, date_str, title, category, description,
                related_documents, related_people, related_media, quote, provenance_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DEMO DATA')
        """, (
            evt["id"], evt["year"], evt["date_str"], evt["title"], evt["category"],
            evt["description"], evt["related_documents"], evt["related_people"],
            evt["related_media"], evt["quote"]
        ))

    # Insert Knowledge Entities
    for ent in KNOWLEDGE_ENTITIES:
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge_entities (
                id, label, category, description, document_id, provenance_type
            ) VALUES (?, ?, ?, ?, ?, 'DEMO DATA')
        """, (
            ent["id"], ent["label"], ent["category"], ent["description"], ent["document_id"]
        ))

    # Insert Knowledge Relations
    for rel in KNOWLEDGE_RELATIONS:
        cursor.execute("""
            INSERT OR REPLACE INTO knowledge_relations (
                id, source_id, target_id, relation, description, citation_id
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            rel["id"], rel["source_id"], rel["target_id"], rel["relation"],
            rel["description"], rel["citation_id"]
        ))

    # Insert Media
    for m in MEDIA_SEED:
        cursor.execute("""
            INSERT OR REPLACE INTO media (
                id, title, type, date, duration, collection, description,
                thumbnail_url, media_url, transcript, audio_narration_text, provenance_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DEMO DATA')
        """, (
            m["id"], m["title"], m["type"], m["date"], m["duration"], m["collection"],
            m["description"], m["thumbnail_url"], m["media_url"], m["transcript"],
            m["audio_narration_text"]
        ))

    # Insert Stories
    for s in STORIES_SEED:
        cursor.execute("""
            INSERT OR REPLACE INTO stories (
                id, slug, title, subtitle, cover_image, excerpt, timeline_year,
                content_json, sources_json, provenance_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'DEMO DATA')
        """, (
            s["id"], s["slug"], s["title"], s["subtitle"], s["cover_image"],
            s["excerpt"], s["timeline_year"], s["content_json"], s["sources_json"]
        ))

    # Add sample default research collection
    cursor.execute("""
        INSERT OR REPLACE INTO research_collections (id, title, description)
        VALUES ('DEFAULT_COLLECTION', 'My Research on Constitutional Debates & Labour Rights', 'Primary source citations saved during research sessions.')
    """)

    conn.commit()
    conn.close()

    # Rebuild FAISS index with seed chunks
    logger.info("Indexing demo chunks into FAISS/Dense index...")
    faiss_service.rebuild()
    faiss_service.add_chunks(all_chunks_for_faiss)
    logger.info("Demo database and FAISS index seeded successfully.")

if __name__ == "__main__":
    seed_database()
