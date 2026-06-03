<p align="center">
  <img width="512" height="768" alt="Anita" src="https://github.com/user-attachments/assets/9b91176f-8f41-4e5c-8fe3-76940503d540" />

  <br><br>
  <a href="https://www.gnu.org/licenses/agpl-3.0">
    <img src="https://img.shields.io/badge/License-AGPL_v3-blue.svg" alt="License: AGPL v3">
  </a>
  <!-- Added Version Badge -->
  <a href="https://github.com/iteranya/anita-cms/releases">
    <img src="https://img.shields.io/badge/Version-0.38-brightgreen.svg" alt="Version 0.38">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img src="https://img.shields.io/badge/Framework-FastAPI-009688.svg" alt="FastAPI">
  </a>
  <a href="https://www.sqlalchemy.org/">
    <img src="https://img.shields.io/badge/ORM-SQLAlchemy-red.svg" alt="SQLAlchemy">
  </a>
</p>
<h1 align="center">Anita Web Studio - The Freelancer's Delivery Stack</h1>
<h3 align="center">Alpha Release: Here Be Dragons</h2>

---

## Why Is Anita?

Anita Web Studio is a self-hosted, full featured web development kit designed for freelancer to create a secure and bespoke website. You use Anita when:

- You are tired of boiler code and writing custom site from scratch
- You have PTSD from clients breaking your website
- You do not want to teach client how to use a CMS Admin Page
- You want a very specific 'website template' that works everytime without the JS Library Rot
- You want something extremely efficient, lightweight, and easy to deploy

In other words, Anita is designed to solve the very specific pain point of every web freelancer out there

## The "One-File" Wonder

*The ultimate portable website.*

Most CMS and Website require a database server, a file server, and a config file. Moving them is a nightmare.

Anita stores EVERYTHING in a single file. 

- Want to backup your site? Copy anita.db and your uploads folder to Google Drive.
- Want to move servers? git pull the repo, paste your anita.db and uploads folder, and you're live.
- Need to scale? Since it uses SQLAlchemy, you can switch to PostgreSQL with one config change if you ever hit 1 million users (but for 99% of us, SQLite is faster, and Anita uses WAL by default).

This is *not* an exaggeration, yes, your entire site, this includes your custom home page and blog page and everything in between. Your configurations, your users, your roles, it's all in a single .db file. 
(No we don't store media file in db, we're not monsters)

Of course this does not apply if you use Anita merely as a Headless CMS, which is another feature she supports.

## Website Scaffolding

*Starting from a blank slate sucks. Anita knows this.*

Because Anita is a **"One-File Wonder"**, you can literally start by copying premade database!

When you run `main.py` for the first time (and Anita sees you don't have an `anita.db` yet), she enters **Interactive Setup Mode**.

1. She looks into the `anita-template/` folder.
2. She lists every `.db` file found there.
3. She asks: *"What are we building today?"*

You *might* see options like:
- `anita-blog.db`
- `anita-cafe.db` 
- `anita-art.db` 
- `anita-sass.db`

(Note: As of writing this, there is only one template available, the default one, sorry)

Once you pick a number, she duplicates that template, renames it to `anita.db`, generates your security keys, and **boom**—your site is pre-populated and ready to go.

**Want to make your own Scaffolds?**
Configure a site exactly how you like it, run the 'seedmakinghelper.py', and drag the sanitized_anita.db into `anita-template/` folder, and rename it to whatever you like. Now you can reuse that setup forever. Perfect if you have repeat clients who ask for similar website every time.

## Margin So Big It Feels Illegal

Because Anita is built on FastAPI (Python), it's comical how lightweight she is
- Low RAM Usage: Unlike Java or Node apps, she sips memory.
- Low CPU Usage: Ideal for the cheapest VPS tier ($3-5/mo) or even a Raspberry Pi.
- No Build Step: No compiling assets on the server. Just run and go.
- No Database Overhead: SQLite runs natively in Python and it's literally just a single file

If you're a freelancer, you can host a dozen instance of Anita in a single server, without having to worry about plugin maintenance, and charge premium for a custom website with branded admin page.

## The Schema Creator

Just like Pocketbase and most BAAS, Anita is designed to ease the use of 'schema creation'.

Usually, if you want a dynamic "Menu" page for a restaurant, you have to code a database model and an API route.

With Anita, you just do this:
- Open the Dashboard: Go to the "Collections" tab.
- Create a Collection: Name it cafe-menu.
- Add Fields: Add a "Text Field" for the Dish Name and a "Number Field" for the Price.
- Check the boxes for access permissions
- Done.

Anita automatically generates a Secure API endpoint. 
Yes, with a single interface, you can create a collection and a **Secure** API Route 

## Export To SSG

*The Client Will Fall In Love With You*

Imagine this, you offer monthly payment to the client. And then say:
> 'If you fail to pay the monthly price, your website will stay online and accessible, though your custom admin dashboard will be disabled'

That's the kind of deal that builds trust and Anita makes this *trivial*

With a simple command, you can generate a 'dist' folder and host that on Github or Netlify.

Current Features:

- Reflects Your Site Structure
- Reflects Your Blog/Page Listing/Search functions (if you use Aina)
- Creates a simple database of all your public page (Page must be marked as public to count)

Upcoming Probably Next Week Features:

- Creates A Reflection Your Collection Database
- Lets Your Custom Pages Display Those Collections

In other words, if you use the Integrated IDE to make your website, you can trust her that any GET public routes become accessible anywhere, even as static sites! 


---

## Architecture

Anita is designed with a simple, foundational architecture in mind. No black box, no magic, what you code is what you get.

| Layer      | Technology                                    |
| :--------- | :-------------------------------------------- |
| **Backend**  | FastAPI, SQLAlchemy                          |
| **Frontend**   | Tailwind, AlpineJS, HTMX                     |

Yes, that's all of them, seriously... 

Checkout requirements.txt if you want to see more.

---

##  Is it Safe?

Short answer: Yes. 
Long answer: We have trust issues.

- Transparent Architecture: No hidden binaries. What you see in main.py is what runs.
- Input Sanitization: We use Ammonia (Rust-based) to scrub every input.
- Discord-Style Permissions: We use ABAC. You can set exactly who can see or edit your cafe-menu. This means you don't give your intern or Karen from accounting the ability to break the website's homepage.

## The Web Studio

These may look like a gorgeous User Friendly Dashboard. But trust me, this is a set of tools you use to create and manage your entire website. This is where you, the developer create the website and everything. Not for the client to add content into the website. You can use the Web Studio to create all the pages of your website, setup the routes of your website, create the schemas and the required API Endpoint, and all the security access control, and the Roles required (defining what client can / cannot do).

#### Main Studio
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-dashboard.png" alt="Admin UI Dashboard" width="700"></p>
<em>This is for your eyes only, a general overview of what the site looks like</em>

#### Pages
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-pages.png" alt="Admin UI Pages" width="700"></p>
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-pages-setting.png" alt="Admin UI Pages Setting" width="700"></p>
<em>In this page, you can create site, (yes, the html front facing site), and the templates and even custom admin pages</em>

#### Structures
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-structure.png" alt="Admin UI Structures" width="700"></p>
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-structure-setting.png" alt="Admin UI Structure Setting" width="700"></p>
<em>This is where you configure the site structure once you have finished making the site. You can also add security here, making sure only certain roles have access to certain sites. Simply create an 'owner' category and put 'menu-edit' page there and the client can easily access `/owner/menu-edit` to change their Cafe Menu</em>

#### Collections (aka Collections)
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-collections.png" alt="Admin UI Collections" width="700"></p>
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-collections-setting.png" alt="Admin UI Collection Settings" width="700"></p>
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-collections-creation.png" alt="Admin UI Collection Creation" width="700"></p>
<em>No more FastAPI Boiler Code just to add new data types. You can make `contact-collection`, but you can also make `cafe-menu`, `art-gallery`, and more, with role based permissions! Anita will create an entire GET/POST/PUT/DELETE route endpoint that accesses these collections you made! And yes, It Is Secure By Default!!!</em>

#### Media & Files
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-media.png" alt="Admin UI Media" width="700"></p>
<em>Tired of Orphan media? Worry not! Anita Keeps Track of Everything!</em>

#### Users & Roles
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/admin-ui-user-and-roles.png" alt="Admin UI User And Roles" width="700"></p>
<em>The heart of security!!! Inspired by Discord, you can create roles with fine-grained permissions.</em>

---

## The AI Part... SIKE! THERE IS NO AI!!!

While Aina used to be a Deepsite Clone, this is no longer the case!

Introducing, Aina Integrated Web IDE!!!

#### Aina Backend Generator
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/aina-generator.png" alt="Aina Backend Generator" width="700"></p>
<em>Browse through the libraries of pre-made alpine component and integrated it into your website! Everything is toggleable with just a click  *and* it is completely safe! The alpine components are designed to interact with Aina Database, aware of all your pages and custom collections too!</em>

#### Aina Frontend Generator
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/aina-editor.png" alt="Aina Frontend IDE" width="700"></p>
<em>Forget about coding logic and focus on UI and presentation! With Tailwind, Awesome Fonts, and AlpineJS baked in, you have everything you need to create a gorgeous site! (Uses Ace Editor, Realtime Tailwind Update, Compiles Tailwind For You, You're Welcome)</em>

But what if I want to code in VS Code? I hear you asking. What if I want to have version control? I hear you asking.

Just use Anita as headless CMS, simple~

#### Asta Markdown Editor
<p align="center"><img src="https://raw.githubusercontent.com/iteranya/anita-cms/main/docs/asta-editor.png" alt="Aina Frontend IDE" width="700"></p>
<em>Built on top of the absolute gorgeous Milkdown Crepe, we present to you Asta Markdown Editor. A gorgeous UI to write your content with minimal fluff. You can save draft and simply publish them! And you can choose which template to use to render the post you've made! You can ship this to the client also! Give them the power to write blog/article without giving them access to the main Studio Panel</em>

---

## For Poweruser: Headless CMS with Security Baked In

Oh so you want to code stuff in react? You want to hydrate your page with json?  Want to skip Aina and write your own Frontend froms scratch??? WELL OF COURSE YOU CAN!!!!

Anita comes with API (documentation pending) that lets you access every part of the CMS through JSON! Even the markdown contents! You can slap in any AI you like on top of Anita and it'll just work perfectly!!!

Not to mention that you still get to use the Admin Panel to manage your users, your pages security, generate all the collections and the strict ACL / RBAC control for each of those collections!!

(Also, hooks for plugin integration feature pending~)

---

## Installation

We recommend using `uv` for lightning-fast dependency management.

```bash
# 1. Clone the repository
git clone https://github.com/iteranya/anita-cms.git
cd anita-cms

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configuration (Optional, main.py can auto generate this part for you)
cp example.env .env
# Edit .env to add your JWT_SECRET

# 5. Run the server
python main.py

# Once running, access your dashboard at:
# http://127.0.0.1:5469/admin
# Follow the on-screen instructions for initial setup.
```

---

## Roadmap

- ~~Editing HTML should be exclusive to Aina~~
- ~~Editing Markdown should be exclusive to Asta~~
- Mitochondria Is The Powerhouse of Cell 
- ~~Bleach Is Not Implemented Properly Yet~~ Done! (With ammonia, bleach is deprecated)
- ~~CSP Configuration Is Still Globally Strict (should be configurable per-page basis)~~ Done! Per-page CSP Implemented!
- CSRF Token (Come on... Why is this so hard???)
- ~~HikarinJS Is Still Opt-in (should be default for all ai generated site)~~ Done! Hikarin JS is first class citizen now~
- ~~Default Pages Still Uses script (Should use HikarinJS Instead)~~ Done! Script exists, but it uses Hikarin middleware now~
- ~~System Page Labels Are Still Manual (Should be abstracted with switches / panel)~~ Done! Made new panel for Structure
- ~~Collection Page Labels Are Still Manual (Should be abstracted with switches / panel)~~ Done! With amazing RBAC Panel
- ~~User Roles and Perms Are Still Manual (Should be abstracted with switches / panel)~~ Done! Discord Flavored ABAC Panel~
- No Tags and Sort Filter Yet (Come on....)
- No Darkmode Yet (seriously?)
- ~~Submission Sanitization not yet implemented~~ Done! (With ammonia, bleach is deprecated)
- Pay Yozzun For Anita's Artwork
- Add Event Bus and Background Handler
- Fediverse/ActivityPub Implementation (I really, really want this but god this is HARD. Stupid Hard.)
- Add better site audit, create snapshot of site structure, schema, role, permission, in JSON to make it possible to git diff
- ~~Asta and Aina doesn't save their own prompt/configuration~~ Done! They save now!
- ~~Remove AI Integration~~ Done! Aina is an IDE now~ 
- ~~Implement Milkdown / Crepe to Asta~~ Done! Asta is Milkdown powered!
- ~~Fix templating system to be True SSR~~ Done! Markdown Pages are now true SSR
- Give Asta (or Aina) a Search Engine Optimization capability 
- Better test coverage
- ~~More graceful Collection Seeding (currently don't exist, actually, only page, roles and config for now)~~ Done! With Starter Kit Feature!
- ~~Category and Labels are the same (should be separated)~~ Done! We have tags (public) and labels (system) now

Terrible Ideas That Won't Go Away

- ~~Let Every User Bring Their Own Admin Page (Actually good idea, but like, CUSTOM Admin Page, not replacing Dashboard)~~ Actually implemented, lmao
- Anita AI Chatbot on Dashboard
- Rewrite Everything In Go
- Rewrite Everything In Rust
- ~~Export to SSG Button (HOW!?!?)~~ HOLY SHIT I ACTUALLY FIGURED IT OUT!!!
- Discord Integration (For... I'm not sure for what... But it'll be cool)
- ~~Make Domain Specific Language For Themes and Plugins~~ No Themes, Only Starter Kits!

---

## QnA

Q: Is this a CMS?
A: *deep sigh* It used to be, but no, not anymore

Q: Is this project ready for..
A: No

Q: Can I use this for...
A: Yes

Q: What if I...
A: No Gatekeeping

Q: Do I need to be good at python???
A: You have to be at least *decent* at python if you wish to add additional features not shipped with base Anita, such as payment gateway and more. But if you only know html, css, js, or even tailwind and alpine? You don't need python.

Q: Documentation? Plugins?
A: After I implement the Event Bridge, because honestly I'll have to rewrite the documentation from scratch if I write it now.

Q: Should I just use Postgre?
A: Do you have 500 editors???

Q: I need version control!
A: Just skip Aina and bring your own Frontend... You can still use Asta for the markdown (unless you want to version control markdown??? In which case, I'll think about adding that feature to Asta). Ah but if you skip Aina you lost the Export to SSG Feature~ Well... Drawbacks, I suppose... You can theoretically version control your SSG, now that I think about it, but you can't version control Aina/Asta editor itself...

Q: Anita? Hikarin? Asta? Aina?
A: THEY'RE CUTE! FIGHT ME!!!

---

## License: AGPL-3.0

AGPL-3.0 - Free To Use, No Gatekeep Allowed.
