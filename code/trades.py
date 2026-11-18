"""IPL 2027 availability, from the official retention lists published on 17 Nov 2026 (retention and trade deadline).
Sources: franchise retention announcements (e.g. rajasthanroyals.com), Wikipedia "List of 2027 Indian Premier League
personnel changes" (retained lists and trades), cross-checked against the released lists reported by Oneindia and Yahoo
Sports on 17 Nov 2026. A player in an IPL 2026 squad who is not in any 2027 retained list was released into the auction pool."""

RETAINED_2027 = {
 "Chennai Super Kings": ["Ruturaj Gaikwad","Sanju Samson","Kartik Sharma","Shivam Dube","Noor Ahmad","Liam Livingstone","Rahul Chahar","Anshul Kamboj","Jack Edwards","Dewald Brevis","Gurjapneet Singh","Akeal Hosein","Jamie Overton","Sarfaraz Khan","Mukesh Choudhary","Ramakrishna Ghosh","Shreyas Gopal","Ayush Mhatre","Urvil Patel"],
 "Delhi Capitals": ["Axar Patel","Rishabh Pant","KL Rahul","Tristan Stubbs","Auqib Nabi","Mukesh Kumar","Ashutosh Sharma","David Miller","Kyle Jamieson","Lungi Ngidi","Sameer Rizvi","Prithvi Shaw","Madhav Tiwari","Zeeshan Ansari","Tripurana Vijay","Vipraj Nigam"],
 "Gujarat Titans": ["Rashid Khan","Shubman Gill","Jos Buttler","Mohammed Siraj","Kagiso Rabada","Prasidh Krishna","Sai Sudharsan","Jason Holder","Rahul Tewatia","Harshal Patel","Washington Sundar","Sai Kishore","Glenn Phillips","Tom Banton","Arshad Khan","Gurnoor Brar","Ashok Sharma","Jayant Yadav","Kumar Kushagra","Anuj Rawat","Manav Suthar","Nishant Sindhu"],
 "Kolkata Knight Riders": ["Cameron Green","Rinku Singh","Sunil Narine","Varun Chakravarthy","Harshit Rana","Ramandeep Singh","Angkrish Raghuvanshi","Finn Allen","Tim Seifert","Vaibhav Arora","Rovman Powell","Manish Pandey","Anukul Roy","Kartik Tyagi","Prashant Solanki","Sarthak Ranjan","Saurabh Dubey"],
 "Lucknow Super Giants": ["Nicholas Pooran","Kuldeep Yadav","Mayank Yadav","Josh Inglis","Abdul Samad","Ayush Badoni","Mohsin Khan","Mitchell Marsh","Mukul Choudhary","Shahbaz Ahmed","Sam Curran","Akshat Raghuwanshi","Aiden Markram","Akash Singh","Arjun Tendulkar","Arshin Kulkarni","Digvesh Rathi","Prince Yadav"],
 "Mumbai Indians": ["Jasprit Bumrah","Arshdeep Singh","Suryakumar Yadav","Rohit Sharma","Tilak Varma","Will Jacks","Naman Dhir","Sherfane Rutherford","Shardul Thakur","Mitchell Santner","Ryan Rickelton","Quinton de Kock","Corbin Bosch","Raj Angad Bawa","Ashwani Kumar","Raghu Sharma"],
 "Punjab Kings": ["Shreyas Iyer","Yuzvendra Chahal","Hardik Pandya","Marcus Stoinis","Marco Jansen","Shashank Singh","Ben Dwarshuis","Prabhsimran Singh","Priyansh Arya","Cooper Connolly","Azmatullah Omarzai","Vijaykumar Vyshak","Yash Thakur","Harpreet Brar","Vishnu Vinod","Xavier Bartlett","Harnoor Pannu","Musheer Khan","Suryansh Shedge"],
 "Rajasthan Royals": ["Yashasvi Jaiswal","Riyan Parag","Ravindra Jadeja","Dhruv Jurel","Jofra Archer","Mohammed Shami","Ravi Bishnoi","Sandeep Sharma","Nandre Burger","Dasun Shanaka","Vaibhav Sooryavanshi","Donovan Ferreira","Sushant Mishra","Shubham Dubey","Manimaran Siddharth","Lhuan-dre Pretorius","Aman Rao Perla","Brijesh Sharma","Yash Raj Punja"],
 "Royal Challengers Bengaluru": ["Virat Kohli","Josh Hazlewood","Phil Salt","Rajat Patidar","Jitesh Sharma","Bhuvneshwar Kumar","Venkatesh Iyer","Rasikh Salam","Krunal Pandya","Yash Dayal","Tim David","Suyash Sharma","Devdutt Padikkal","Jacob Duffy","Nuwan Thushara","Romario Shepherd","Jordan Cox","Abhinandan Singh","Kanishk Chouhan","Vicky Ostwal"],
 "Sunrisers Hyderabad": ["Heinrich Klaasen","Pat Cummins","Abhishek Sharma","Ishan Kishan","Nitish Kumar Reddy","T. Natarajan","Khaleel Ahmed","Nathan Ellis","Salil Arora","Eshan Malinga","Brydon Carse","Smaran Ravichandran","Aniket Verma","Harsh Dubey","Krains Fuletra","Praful Hinge","Sakib Hussain","Shivang Kumar"],
}

AS_OF = "17 Nov 2026"
TRADES = {  # player name: (from, to)
    "Kuldeep Yadav": ("Delhi Capitals", "Lucknow Super Giants"),
    "Rishabh Pant": ("Lucknow Super Giants", "Delhi Capitals"),
    "Hardik Pandya": ("Mumbai Indians", "Punjab Kings"),
    "Arshdeep Singh": ("Punjab Kings", "Mumbai Indians"),
    "Liam Livingstone": ("Sunrisers Hyderabad", "Chennai Super Kings"),
    "Khaleel Ahmed": ("Chennai Super Kings", "Sunrisers Hyderabad"),
    "Nathan Ellis": ("Chennai Super Kings", "Sunrisers Hyderabad"),
    "T Natarajan": ("Delhi Capitals", "Sunrisers Hyderabad"),
    "Harshal Patel": ("Sunrisers Hyderabad", "Gujarat Titans"),
    "Mohammed Shami": ("Lucknow Super Giants", "Rajasthan Royals"),
    "Manimaran Siddharth": ("Lucknow Super Giants", "Rajasthan Royals"),
    "Jack Edwards": ("Sunrisers Hyderabad", "Chennai Super Kings"),
    "Sam Curran": ("Rajasthan Royals", "Lucknow Super Giants"),
    "Zeeshan Ansari": ("Sunrisers Hyderabad", "Delhi Capitals"),
}

NOT_AVAILABLE = {  # player name: reason he cannot be signed for IPL 2027
    "Harry Brook": "banned from the IPL until the 2028 auction (late withdrawal, 2025)",
    "Andre Russell": "retired from the IPL (Nov 2025)",
    "Ravichandran Ashwin": "retired from the IPL (Aug 2025)",
    "Mahendra Singh Dhoni": "retired as a player (17 Nov 2026); now CSK mentor",
    "Ajinkya Rahane": "retired (30 Jul 2026)",
}
_BD = "not among the seven Bangladesh players registered for the 2027 auction (BCB, Nov 2026)"
NOT_AVAILABLE.update({n: _BD for n in ("Liton Das", "Tanzid Hasan", "Mahedi Hasan", "Tanzim Sakib", "Nasum Ahmed",
                                       "Shakib Al Hasan", "Mohammad Saif Hassan", "Parvez Emon", "Jaker Ali Anik")})
UNSOLD_2026 = {"Daryl Mitchell", "Mujeeb Ur Rahman", "Maheesh Theekshana"}   # went unsold at the IPL 2026 auction


_ALIAS = {"Namboori Tilak Varma": "Tilak Varma", "Patrick Cummins": "Pat Cummins", "Lokesh Rahul": "KL Rahul",
          "Nitish Reddy": "Nitish Kumar Reddy", "William Jacks": "Will Jacks", "Vyshak Kumar": "Vijaykumar Vyshak",
          "T Natarajan": "T. Natarajan", "Aman Rao": "Aman Rao Perla"}
TEAM_2027 = {n: t for t, ns in RETAINED_2027.items() for n in ns}


_DUP = {"Abdul Samad", "Rashid Khan"}   # names shared by two players in the data pack


def team27(name, team26=None):
    """2027 team from the official retained lists (None = in no squad)."""
    if name in _DUP and not (isinstance(team26, str) and team26 not in ("-", "")):
        return None   # the namesake who was in no IPL squad
    return TEAM_2027.get(_ALIAS.get(name, name))


def released_by(name, team26):
    """The team that released him on 17 Nov 2026, or None."""
    ok = isinstance(team26, str) and team26 not in ("-", "")
    return team26 if ok and team27(name, team26) is None and name not in NOT_AVAILABLE else None


def route(name, team26):
    """How RR could get this player for 2027: (short label, plain explanation)."""
    if name in NOT_AVAILABLE:
        return "Not available", NOT_AVAILABLE[name]
    t = team27(name, team26)
    if t == "Rajasthan Royals":
        return "Already at RR", "in RR's retained squad for 2027"
    if t:
        return "Under contract", f"retained by {t} for 2027, so not in the auction (only a trade could move him)"
    rb = released_by(name, team26)
    if rb:
        return "Auction", f"released by {rb} on {AS_OF}: in the 16 Dec auction if he registers"
    return "Auction", ("in no IPL squad; went unsold at the 2026 auction" if name in UNSOLD_2026
                       else "in no IPL squad, so in the auction if he registers")

# RR going into the auction (official, 17 Nov 2026)
RR_PURSE, RR_SLOTS, RR_OVERSEAS_SLOTS = 27.05, 6, 3
RR_RELEASED = ["Shimron Hetmyer", "Tushar Deshpande", "Adam Milne", "Kuldeep Sen", "Yudhvir Singh", "Kwena Maphaka",
               "Vignesh Puthur", "Ravi Singh", "Emanjot Singh Chahal"]
# Bangladesh players: BCB named seven registered for the 2027 auction (Mustafizur Rahman, Nahid Rana, Rishad Hossain,
# Hasan Mahmud, Towhid Hridoy, Taskin Ahmed, Shoriful Islam)
BD_REGISTERED = {"Mustafizur Rahman", "Nahid Rana", "Rishad Hossain", "Mohammad Rishad Hossain", "Hasan Mahmud", "Towhid Hridoy", "Taskin Ahmed",
                 "Shoriful Islam"}


# Confirmed international-cap status and ages (as of 17 Nov 2026; Wikipedia cap lists, ESPNcricinfo, IPL profiles).
# Capped = played at least one senior men's international for India in any format.
CAPPED = {"Anshul Kamboj": "India Test debut Jul 2025, ODI Oct 2026",
          "Sai Kishore": "India T20I debut Oct 2023 (Asian Games)",
          "Vaibhav Sooryavanshi": "India T20I debut 4 Jul 2026, India's youngest international debutant"}
UNCAPPED = {"Rasikh Salam", "M Shahrukh Khan", "Vyshak Kumar", "Digvesh Rathi", "Suyash Sharma", "Ayush Mhatre",
            "Priyansh Arya", "Angkrish Raghuvanshi", "Sameer Rizvi", "Abishek Porel", "Abdul Samad", "Kartik Tyagi",
            "Brijesh Sharma", "Shashank Singh", "Ashutosh Sharma"}
AGE = {"Vaibhav Sooryavanshi": 15, "Ayush Mhatre": 19, "Angkrish Raghuvanshi": 21, "Sameer Rizvi": 22, "Suyash Sharma": 23,
       "Abishek Porel": 24, "Priyansh Arya": 25, "Abdul Samad": 25, "Anshul Kamboj": 25, "Rasikh Salam": 26,
       "Digvesh Rathi": 26, "Kartik Tyagi": 26, "Brijesh Sharma": 27, "Vyshak Kumar": 29, "M Shahrukh Khan": 31}
