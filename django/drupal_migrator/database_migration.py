import contextlib
import csv
import io
import json
import logging
import os
import pathlib
import re
from collections import defaultdict, Iterable
from datetime import datetime
from textwrap import shorten
from typing import Dict

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.core.files.images import ImageFile
from taggit.models import Tag
from wagtail.wagtailimages.models import Image

from core.fs import is_image
from core.models import ComsesGroups, Institution, Platform, Event, Job
from core.summarization import summarize_to_text
from home.models import Journal, FaqEntry
from library.models import (Contributor, Codebase, CodebaseRelease, CodebaseTag, License,
                            ReleaseContributor, OPERATING_SYSTEMS, CodebaseReleaseDownload)
from .utils import get_first_field, get_field, get_field_attributes, to_datetime

logger = logging.getLogger(__name__)

PROFILE_PICTURES_PATH = 'incoming/pictures'

FAQ_ENTRIES = """id,category,question,answer
    0,abm,"What are agent-based models (ABMs)?","Agent-based models are (computational) models of a heterogeneous population of agents and their interactions. The result of the micro-level interactions can be interesting macro-level behavior like cooperation, segregation, fashion, culture, etc. ABMs are also known as multi-agent systems, agent-based systems etc., and is an important field in computer science where agent-based models are developed to do tasks, like searching for information on the internet. Within social science we are interested in agent-behavior that is based on our understanding of human decision making. Agents can represent individuals, households, firms, nations, depending on the application. The heterogeneity of agents is an important aspect of ABM. Heterogeneity can originate from differences is location, knowledge, wealth, social connections, cognitive processes, experience, motivations, preferences, etc. Agents can interact in various ways such as changing the shared environment by harvesting or pollution, exchange of information and resources, and by imitation."
    1,abm,"When should I use agent-based models?","It is important to have a clear research question what kind of emergent process one likes to study. Often scholars use ABM to describe a lot of details of a complicated system. The resulting model is often not useful since it is too complicated to perform a rigorous analysis required for understanding the behavior of the model. Often an agent-based model is not necessary. When there is a small set of agents, or a very large of agents who interact randomly, sets of differential equations, such as system dynamics models, may be a suitable tool too. ABMs are especially useful when the agents interact in non-random ways, like social networks, of spatial explicit ecological systems. Furthermore, they are useful to test different cognitive processes and heterogeneity of decision-making processes in a population."
    2,abm,"How do I use agent-based models?","Models are tools for communication, education, exploration and experimentation. Models are not holy tools for prediction, especially not for non-linear systems. Unfortunately, there is a lot of misunderstanding about models. People who are not very familiar with them have sometimes high expectations of the details that are included. A common critique of non-modelers is that more details need to be included. But more details might only make the model less useful for exploration of the parameter space. The goal is to make “the models as simple as possible, but no simpler than that”. One confuses often the use of a model with a description of the real systems."
    3,abm,"How do I implement agent-based models?","There are a number of ABM platforms like Swarm, Starlogo, Netlogo, Mason, Cormas, Repast, etc (List of ABM Platforms can be found here). The main benefits of these platforms are the provision of a graphical interface, an open source community who may develop similar models you are interested in, and libraries. A drawback is that these platforms are not always userfriendly and that libraries only include the more straightforward algorithms. One can also develop ABMs in more standard packages like MATLAB when one is already familiar with such a platform. A good platform to get started is Netlogo, which has good tutorials and a elaborative library of demo models. For more experienced modelers, a platform like Repast might be more applicable since the run time is faster and more tailored procedures can be implemented."
    4,abm,"How do I validate and calibrate agent-based models?","The terms validation and calibration originate in engineering and are sensitive to many social scientists. What we want to test is how well our model explains the data compared with alternative models. Therefore it is important to use different models of decision making. Human decision making is so complicated that we do not have the illusion to argue that we have the true model. Model comparison is, however, not a straightforward activity. There are different dimensions in which a model may be evaluated. One way social scientists test models is use maximum likelihood estimation. Since more complicated models with more degrees of freedom result in better fits, some scholars use a penalty for the complexity of the model. Especially the use of minimum description length might be a promising tool. Increasingly experimental researchers and agent-based modeling start to be combined. Traditionally experiments where used to challenge the standard model of rational choice, nowadays alternative models are tested in more complicated dynamic and spatial settings, in the lab and in the field. This may lead to better tested alternative models that one can use in ABMS. Other ways to evaluate models is the participatory model development with stakeholders, or the use of Turing-tests."
    5,abm,"How do I document agent-based models?","A standard rule is that one should be able to replicate the basic results of your research. Simple models should be documented in such a way, that a colleague is able to reimplement the model and derive similar results. Several noteworthy results from models published in high level journals have been difficult to replicate. At the very least, some assumptions made in the original model led to doubt about whether the results were robust. At CoMSES Net we recommend the [ODD protocol (Grimm et al., 2006)](/resources/standards/) as a starting point for model documentation."
    6,abm,"What is the difference between ABMs and system dynamics?","System dynamics is characterized by causal feedback loops and is formalized by sets of differential equations which are numerically solved in user-friendly packages like Stella and Vensim. One can write simple agent-based models in packages like Stella and Vensim, using arrays of differential equations and a fixed topology of interactions. But this use of system dynamics packages restrict the possibilities of more dynamic interactions of agents, heterogeneity of agents, more complex recursive reasoning processes."
    7,abm,"What is the difference between ABMs and Markov processes?","A Markov process is a random process whose future probabilities are determined by its most recent values. Sometimes ABM fits this description very well, but in many cases the decisions are dependent on the state of the systems of more than one step ago. This is especially the case when agents learn or have a memory."
    8,abm,"What are complex systems?","ABMs are especially used to study complex systems. With complex systems we refer to systems that use simple micro-level rules that generate macro-level phenomena. These emergent phenomena can not be explained by the micro-level units alone. The interactions of the units lead to a nonlinear transformation to macro-level phenomena. For example, we can not understand the emergence of ant-colonies by studying one ant. Complex systems are different from complicated systems. Complex systems are in fact simplified versions of very complicated systems. Scholars studying complex systems and complexity are interested in discovering the basic underlying rules that describe most of the phenomena, not the details for specific empirical applications."
    9,abm,"What are the decision rules used by agents?","This is a major open question in the field of ABMs. It is well known that rational choice theory which assumes selfish rational decision makers is a reasonable model of decision making only in specific conditions, such as high competitive markets. In most other situations we lack a standard model, but there are a lot of insights of regularities and anomalies in decision making. Instead of assuming selfish individuals with perfect information, we often assume agents who have simple heuristics of satisfying behavior. Cognitive scientists test many types of models on experimental data, and this provides us some useful models like reinforcement learning models, or other regarding preferences. Another way to elicit heuristics for decision making of the agents is to interview stakeholders on their decision making. Although people can not clearly express how they make decisions, they may provide useful information."
    10,general,"How do I become a CoMSES Member?","As a scientific community of practice, members of the CoMSES Network have access to a suite of [community](/community/) [resources](/resources/) and also share a responsibility to contribute to the community. There are two categories of membership in the network: Basic and Full Members.\n\nTo view the benefits and responsibilities of CoMSES membership: please visit the [CoMSES Membership Page](/accounts/signup/)."
    11,general,"How do I add a calendar event?","Signed-in CoMSES members can add calendar events to our site calendar, such as upcoming conferences or workshops. To add an event, go to the Events Calendar and choose [Add Event](/events/create)."
    12,general,"How do I propose a new modeling platform as a resource?","Please submit your suggestions to update or add a platform to the [Modeling Platforms](/resources/modeling-platforms/) list via our [contact page](/about/contact/)."
    13,"model-library","How do I add a model to the Computational Model Library (CML)?","To contribute a model with its associated metadata and documentation to the Library, you must be a [CoMSES Net member](/accounts/signup/) and signed in. \n\nThe [model upload system](/codebases/create) will guide you through several steps and collect important contextual metadata about your computational model, including references to associated publications, narrative documentation of your model, the model codebase itself, and additional metadata like the programming platform, programming language, and other software dependencies, etc. The Computational Model Library requires that narrative documentation be provided to help others understand the purpose and structure of your computational model and facilitate reuse and reproducibility. The ODD protocol (referenced below) is recommended as a format for documenting your computational models, but not a hard requirement."
    14,"model-library","How do I find models in the library on a specific topic?","You can [search the computational model library by tags, author, date, and general keywords in the description and code](/search/codebases/)."
    15,"model-library","How do I find the newest models in the Computational Model Library?","Sort by date while [browsing the CML](/codebases/)."
    16,"model-library","How do I use the CML with journal submissions?","This information needs to be updated manually."
    17,"model-library","What kind of computational models can be archived in the CML?","Although our focus is on agent-based models on social and ecological systems, we are open to broader computational models including geosimulation, cellular automata, dynamic networks, etc. [Contact us](/about/contact/) if you have any questions!"
    18,"model-library","What is publishing a model and how is it done?","You must explicitly choose to Publish a computational model in the CML to make it publicly accessible and discoverable. You may choose to keep a model unpublished, if for example it is associated with a publication under review, and you do not wish to make the model public until the paper has been published."
    19,"model-library","What does it mean to submit a model for review and how does it work?","Model authors may request that their models be peer reviewed for structural completeness and fulfilling [community standards](/resources/standards/). Models that meet these modeling standards will be certified as Peer Reviewed and be badged as well as be eligible for inclusion on our [home page](/) as Featured Content.\n\nFor more information, please see the [Peer Review page](/faq/peer-review)."
    20,"model-library","What is a permanent handle?","A permanent handle is a unique string of characters used to identify a specific piece of academic output, such as a journal publication, [dataset](https://datacite.org) or [software](https://www.force11.org/software-citation-principles). Handles are defined and managed by [the Handle System](http://handle.net/), an international consortium that includes DOIs. DOIs are a pseudo commercial implementation of the handle.net system, especially useful for commercial publishers. In the spirit of open source we prefer the free handle system but you can also mint DOIs for your codebases via our integration with [Zenodo](https://zenodo.org). Arizona State University (ASU) is a registered service provider with the Handle System, and CoMSES has an arrangement with the ASU Libraries to register our permanent content items (models) through the ASU registered ID.\n\nCoMSES’ current policy is to mint handles for peer reviewed models (i.e., those that have passed the CoMSES Net peer review process) and models that have been reviewed as part of a published journal paper. For example, this replication of Artificial Anasazi has been certified and has a permanent handle (http://hdl.handle.net/2286.0/oabm:2222 (link is external)) which can be found in the model’s citation information."
    21,"model-library","How do I delete my computational model from the CML?",\"Once a model is published in the CML, they become a matter of public record and in general cannot be removed from the CML except for extraordinary circumstances (e.g., confidentiality, privacy, or licensing issues).\n\n With that understanding in mind, if you must retract a model from the library, you will need to [contact us](/about/contact/) to explain your situation in detail.\""""


LICENSES = """id,name,url
    0,"None",""
    1,"GPL-2.0",http://www.gnu.org/licenses/gpl-2.0.html
    2,"GPL-3.0",http://www.gnu.org/licenses/gpl-3.0.html
    3,"Apache-2.0",http://www.apache.org/licenses/LICENSE-2.0.html
    4,"CC-BY-3.0",http://creativecommons.org/licenses/by/3.0/
    5,"CC-BY-SA-3.0",http://creativecommons.org/licenses/by-sa/3.0/
    6,"CC-BY-ND-3.0",http://creativecommons.org/licenses/by-nd/3.0
    7,"CC-BY-NC-3.0",http://creativecommons.org/licenses/by-nc/3.0
    8,"CC-BY-NC-SA-3.0",http://creativecommons.org/licenses/by-nc-sa/3.0
    9,"CC-BY-NC-ND-3.0",http://creativecommons.org/licenses/by-nc-nd/3.0
    10,"AFL-3.0",http://www.opensource.org/licenses/afl-3.0.php
    11,"BSD-2-Clause",http://opensource.org/licenses/BSD-2-Clause
    12,"MIT", https://opensource.org/licenses/MIT"""

JOURNALS = """id,name,url,description
    0,Adaptive Behavior,https://us.sagepub.com/en-us/nam/journal/adaptive-behavior,"The official journal of the International Society for Adaptive Behavior (ISAB) that publishes peer-reviewed articles on adaptive behavior in living organisms and autonomous artificial systems. &quot;The journal explores mechanisms, organizational principles, and architectures that can be expressed in computational, physical, or mathematical models related to the both the functions and dysfunctions of adaptive behavior.&quot;"
    1,Advances in Complex Systems,http://www.worldscientific.com/page/acs/aims-scope,"A journal that aims to provide a unique medium of communication for multidisciplinary approaches, either empirical or theoretical, to the study of complex systems. The latter are seen as systems comprised of multiple interacting components, or agents."
    2,Artificial Life,http://www.mitpressjournals.org/loi/artl,"A journal “that investigates the scientific, engineering, philosophical, and social issues involved in our rapidly increasing technological ability to synthesize life-like behaviors from scratch in computers, machines, molecules, and other alternative media.”"
    3,Complex Adaptive Systems Modeling,http://www.casmodeling.com/,"A multidisciplinary modeling and simulation journal that serves as a forum for original, high-quality peer-reviewed papers with a specific interest and scope limited to agent-based and complex network-based modeling paradigms for Complex Adaptive Systems (CAS)."
    4,Computational and Mathematical Organization Theory,https://link.springer.com/journal/10588,"A journal focused on advancing “the state of science in formal reasoning, analysis, and system building drawing on and encouraging advances in areas at the confluence of social networks, artificial intelligence, complexity, machine learning, sociology, business, political science, economics, and operations research.”"
    5,Ecological Modeling,https://www.journals.elsevier.com/ecological-modelling/,"A journal “concerned with the use of mathematical models and systems analysis for the description of ecological processes and for the sustainable management of resources.”"
    6,Environmental Modelling & Software,http://www.journals.elsevier.com/environmental-modelling-and-software/,"Environmental Modelling & Software publishes contributions, in the form of research articles, reviews, short communications as well as software and data news, on recent advances in environmental modelling and/or software. The aim is to improve our capacity to represent, understand, predict or manage the behaviour of environmental systems at all practical scales, and to communicate those improvements to a wide scientific and professional audience."
    7,Journal of Artificial Societies and Social Simulation (JASSS),http://jasss.soc.surrey.ac.uk/,"A journal dedicated to the “exploration and understanding of social processes by means of computer simulation.”"
    8,Journal of Complexity,https://www.journals.elsevier.com/journal-of-complexity/,"A multidisciplinary journal focused on the mathematics and algorithms of computational complexity."
    9,Swarm Intelligence Journal,https://link.springer.com/journal/11721,"A journal focused on the “theoretical, experimental, and practical aspects of swarm intelligence. Emphasis is given to such topics as the modeling and analysis of collective biological systems; application of biological swarm intelligence models to real-world problems; and theoretical and empirical research in ant colony optimization, particle swarm optimization, swarm robotics, and other swarm intelligence algorithms.”"
    10,Structure and Dynamics,http://escholarship.org/uc/imbs_socdyn_sdeas,\"An eJournal that examines “aspects of human evolution, social structure and behavior, culture, cognition, or related topics. Our goal is to advance the historic mission of anthropology in the broadest sense to describe and explain the range of variation in human biology, society, culture and civilization across time and space.”\""""

PLATFORMS = """id,active,name,url,description
    0,f,other,NULL,''
    1,t,Ascape,http://ascape.sourceforge.net/,"Ascape is an innovative tool for developing and exploring general-purpose agent-based models. It is designed to be flexible and powerful, but also approachable, easy to use and expressive. Models can be developed in Ascape using far less code than in other tools. Ascape models are easier to explore, and profound changes to the models can be made with minimal code changes. Ascape offers a broad array of modeling and visualization tools."
    2,f,Breve,http://www.spiderland.org/,"breve is a free, open-source software package which makes it easy to build 3D simulations of multi-agent systems and artificial life. Using Python, or using a simple scripting language called steve, you can define the behaviors of agents in a 3D world and observe how they interact. breve includes physical simulation and collision detection so you can simulate realistic creatures, and an OpenGL display engine so you can visualize your simulated worlds."
    3,t,Cormas,http://cormas.cirad.fr/en/outil/outil.htm,"Cormas is a simulation platform based on the VisualWorks programming environment which allows the development of applications in the object-oriented programming language SmallTalk. Cormas pre-defined entities are SmallTalk generic classes from which, by specialization and refining, users can create specific entities for their own model."
    4,t,DEVS-Suite,http://acims.asu.edu/software/devs-suite/,"DEVS-Suite 3.0.0 is the first discrete-event/discrete-time simulator that offers the capability to generate and visualize Superdense Time Trajectories. Two new types of time-based trajectories (plots) are introduced to the Business Intelligence Reporting Tool (BIRT) and then integrated into the DEVS-Suite 2.1.0. This simulator supports a rich set of menu-driven capabilities to create and customize two new kinds of time-based trajectories."
    5,t,EcoLab,http://ecolab.sourceforge.net/,"EcoLab is both the name of a software package and a research project that is looking at the dynamics of evolution."
    6,t,Mason,http://cs.gmu.edu/~eclab/projects/mason/,"MASON is a fast discrete-event multiagent simulation library core in Java, designed to be the foundation for large custom-purpose Java simulations, and also to provide more than enough functionality for many lightweight simulation needs. MASON contains both a model library and an optional suite of visualization tools in 2D and 3D."
    7,f,Mass,http://mass.aitia.ai/,"A modeling platform consisting of the Functional Agent-based Language for Simulation (FABLES) programming language, a participatory simulations software, and the Model Exploration Module (MEME), which manages experiments for batch processing and analysis."
    8,f,Mobildyc,http://w3.avignon.inra.fr/mobidyc/index.php/English_summary,"Mobidyc is a software project that aims to promote Individual-Based Modelling in the field of ecology, biology and environment. It is the acronym for MOdelling Based on Individuals for the DYnamics of Communities."
    9,t,NetLogo,http://ccl.northwestern.edu/netlogo/,"NetLogo is a multi-agent programmable modeling environment. It is used by tens of thousands of students, teachers and researchers worldwide. It also powers HubNet participatory simulations. It is authored by Uri Wilensky and developed at the CCL. You can download it free of charge."
    10,t,Repast,http://repast.github.io,"The Repast Suite is a family of advanced, free, and open source agent-based modeling and simulation platforms that have collectively been under continuous development for over 15 years."
    11,t,SeSAm,http://www.simsesam.de/,"SeSAm (Shell for Simulated Agent Systems) provides a generic environment for modeling and experimenting with agent-based simulation. We specially focused on providing a tool for the easy construction of complex models, which include dynamic interdependencies or emergent behaviour."
    12,t,StarLogo,http://education.mit.edu/portfolio_page/starlogo-tng/,"StarLogo TNG is a downloadable programming environment that lets students and teachers create 3D games and simulations for understanding complex systems."
    13,t,Swarm,http://www.swarm.org/,"Swarm is a platform for agent-based models (ABMs) that includes a conceptual framework for designing, describing, and conducting experiments on ABMs"
    14,t,AnyLogic,http://www.anylogic.com/,"A Java Eclipse-based modeling platform that supports System Dynamics, Process-centric (AKA Discrete Event), and Agent Based Modeling."
    15,t,MATLAB,http://www.mathworks.com/products/matlab/,"MATLAB is a multi-paradigm numerical computing environment and programming language developed by MathWorks."
    16,t,AgentBase,http://agentbase.org/,"AgentBase.org allows you to do Agent Based Modeling (ABM) in the browser. You can edit, save, and share models without installing any software or even reloading the page. Models are written in Coffeescript and use the AgentBase library."
    17,f,"Agent Modeling Platform (AMP)",http://www.eclipse.org/amp/,"The AMP project provides extensible frameworks and exemplary tools for representing, editing, generating, executing and visualizing agent-based models (ABMs) and any other domain requiring spatial, behavioral and functional features."
    18,t,AgentScript,http://agentscript.org/,"AgentScript is a minimalist Agent Based Modeling (ABM) framework based on NetLogo agent semantics. Its goal is to promote the Agent Oriented Programming model in a highly deployable CoffeeScript/JavaScript implementation. "
    19,t,CRAFTY,https://www.wiki.ed.ac.uk/display/CRAFTY/Home,"CRAFTY is a large-scale ABM of land use change. It has been designed to allow efficient but powerful simulation of a wide range of land uses and the goods and services they produce. It is fully open-source and can be used without the need for any programming."
    20,t,ENVISION,http://envision.bioe.orst.edu/,"ENVISION is a GIS-based tool for scenario-based community and regional integrated planning and environmental assessments.  It provides a robust platform for integrating a variety of spatially explicit models of landscape change processes and production for conducting alternative futures analyses."
    21,t,FLAME,http://flame.ac.uk/,"FLAME is a generic agent-based modelling system which can be used to development applications in many areas. It generates a complete agent-based application which can be compiled and built on the majority of computing systems ranging from laptops to HPC super computers."
    22,t,GAMA,https://github.com/gama-platform,"GAMA is a modeling and simulation development environment for building spatially explicit agent-based simulations."
    23,t,"Insight Maker",https://insightmaker.com/,"Use Insight Maker to start with a conceptual map of your Insight and then convert it into a complete simulation model. Insight Maker supports extensive diagramming and modeling features that enable you to easily create representations of your system."
    24,t,JAMSIM,https://github.com/compassresearchcentre/jamsim,"JAMSIM is a framework for creating microsimulation models in Java. It provides code and packages for common features of microsimulation models for end users."
    25,t,JAS-mine,http://www.jas-mine.net/,"JAS-mine is a Java platform that aims at providing a unique simulation tool for discrete-event simulations, including agent-based and microsimulation models."
    26,t,Jason,https://github.com/jason-lang/jason,"Jason is an interpreter for an extended version of AgentSpeak. It implements the operational semantics of that language, and provides a platform for the development of multi-agent systems, with many user-customisable features. Jason is available as Open Source, and is distributed under GNU LGPL."
    27,t,MADeM,http://www.uv.es/grimo/jmadem/,"The MADeM (Multi-modal Agent Decision Making) model provides agents with a general mechanism to make socially acceptable decisions. In this kind of decisions, the members of an organization are required to express their preferences with regard to the different solutions for a specific decision problem. The whole model is based on the MARA (Multi-Agent Resource Allocation) theory, therefore, it represents each one of these solutions as a set of resource allocations."
    28,t,MATSim,http://www.matsim.org/,\"MATSim is an open-source framework to implement large-scale agent-based transport simulations.\""""


def flatten(ls):
    return [item for sublist in ls for item in sublist]


def load_data(model, s: str):
    f = io.StringIO(s.strip())
    rows = csv.DictReader(f)

    instances = []
    for row in rows:
        instances.append(model(**row))

    model.objects.bulk_create(instances)
    # TODO: set sequence number to start after last value when moved over to Postgres


@contextlib.contextmanager
def suppress_auto_now(model_classes, *field_names):
    _original_values = {}
    for field_name in field_names:
        _ms = model_classes if isinstance(model_classes, Iterable) else [model_classes]
        for model in _ms:
            field = model._meta.get_field(field_name)
            _original_values[field] = {
                'auto_now': field.auto_now,
                'auto_now_add': field.auto_now_add,
            }
            field.auto_now = False
            field.auto_now_add = False
    try:
        yield
    finally:
        for field, values in _original_values.items():
            field.auto_now = values['auto_now']
            field.auto_now_add = values['auto_now_add']


class Extractor:
    def __init__(self, data):
        self.data = data

    @staticmethod
    def sanitize_name(name: str):
        # return re.sub(r'[^\w]', '')

        return ' '.join(name.split()).replace('.', '').title()

    @staticmethod
    def sanitize(data: str, max_length: int = None, strip_whitespace=False) -> str:
        if strip_whitespace:
            _sanitized_data = data.replace(' ', '').lower()
        else:
            _sanitized_data = data.strip().lower()
        if max_length is not None:
            if len(_sanitized_data) > max_length:
                logger.warning("data exceeded max length %s: %s", max_length, data)
                return shorten(_sanitized_data, max_length)
        return _sanitized_data

    @staticmethod
    def sanitize_text(data: str, max_length: int = None) -> str:
        _sanitized_data = BeautifulSoup(data.strip(), "lxml").get_text()
        if max_length is not None:
            return shorten(_sanitized_data, max_length)
        return _sanitized_data

    @staticmethod
    def int_to_bool(integer_value, default=False) -> bool:
        try:
            return bool(int(integer_value))
        except:
            logger.debug("Could not convert %s to bool", integer_value)
            return default

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'r', encoding='UTF-8') as f:
            data = json.load(f)
            return cls(data)


class EventExtractor(Extractor):
    EVENT_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

    @staticmethod
    def parse_event_date_string(date_string: str):
        return datetime.strptime(date_string, EventExtractor.EVENT_DATE_FORMAT)

    def _extract(self, raw_event, user_id_map: Dict[str, int]) -> Event:
        summary = self.sanitize_text(get_first_field(raw_event, 'body', attribute_name='summary', default=''),
                                     max_length=300)
        description = self.sanitize_text(get_first_field(raw_event, 'body'))
        return Event(
            title=raw_event['title'].strip(),
            date_created=to_datetime(raw_event['created']),
            last_modified=to_datetime(raw_event['changed']),
            summary=summary,
            description=description,
            early_registration_deadline=to_datetime(get_first_field(raw_event, 'field_earlyregistration')),
            submission_deadline=to_datetime(get_first_field(raw_event, 'field_submissiondeadline')),
            start_date=self.parse_event_date_string(get_first_field(raw_event, 'field_eventdate')),
            end_date=self.parse_event_date_string(get_first_field(raw_event, 'field_eventdate', 'value2')),
            submitter_id=user_id_map.get(raw_event['uid'], 3),
        )

    def extract_all(self, user_id_map: Dict[str, int]):
        events = [self._extract(raw_event, user_id_map) for raw_event in self.data]
        with suppress_auto_now(Event, 'last_modified', 'date_created'):
            Event.objects.bulk_create(events)


class JobExtractor(Extractor):
    def _extract(self, raw_job: Dict, user_id_map: Dict[str, int]):
        description = self.sanitize_text(get_first_field(raw_job, 'body'))
        summary = summarize_to_text(description, sentences_count=2)
        return Job(
            title=raw_job['title'].strip(),
            date_created=to_datetime(raw_job['created']),
            last_modified=to_datetime(raw_job['changed']),
            summary=summary,
            description=description,
            submitter_id=user_id_map.get(raw_job['uid'], 3)
        )

    def extract_all(self, user_id_map: Dict[str, int]):
        jobs = []
        for forum_post in self.data:
            if forum_post['forum_tid'] == "13":
                jobs.append(self._extract(forum_post, user_id_map))
        with suppress_auto_now(Job, 'last_modified', 'date_created'):
            Job.objects.bulk_create(jobs)


class UserExtractor(Extractor):

    (ADMIN_GROUP, EDITOR_GROUP, FULL_MEMBER_GROUP, REVIEWER_GROUP) = ComsesGroups.initialize()

    @staticmethod
    def _extract(raw_user):
        """ assumes existence of editor, reviewer, full_member, admin groups """
        username = Extractor.sanitize(raw_user['name'], strip_whitespace=True)
        email = Extractor.sanitize(raw_user['mail'])
        status = raw_user['status']
        if not all([username, email]):
            logger.warning("No username or email set: %s", [username, email])
            return
        user, created = User.objects.get_or_create(
            username=username,
            email=email,
            is_active=self.int_to_bool(status),
            defaults={
                "date_joined": to_datetime(raw_user['created']),
                "last_login": to_datetime(raw_user['login']),
            }
        )
        member_profile = user.member_profile
        # extract picture
        picture_dict = raw_user['picture']
        if picture_dict:
            picture_path = pathlib.Path(PROFILE_PICTURES_PATH, picture_dict['filename'])
            if picture_path.exists() and is_image(str(picture_path)):
                with picture_path.open('rb') as f:
                    avatar = Image.objects.create(
                        title="{0} avatar".format(username),
                        file=ImageFile(f),
                        uploaded_by_user=user)
                    member_profile.picture = avatar

        user.drupal_uid = raw_user['uid']
        roles = raw_user['roles'].values()
        member_profile.timezone = raw_user['timezone']
        member_profile.save()
        if 'administrator' in roles:
            user.is_staff = True
            user.is_superuser = True
            user.save()
            user.groups.add(UserExtractor.ADMIN_GROUP)
            user.groups.add(UserExtractor.FULL_MEMBER_GROUP)
        if 'comses member' in roles:
            user.groups.add(UserExtractor.FULL_MEMBER_GROUP)
            user.groups.add(UserExtractor.REVIEWER_GROUP)
        if 'comses editor' in roles:
            user.groups.add(UserExtractor.EDITOR_GROUP)
        if 'comses reviewer' in roles:
            user.groups.add(UserExtractor.REVIEWER_GROUP)
        return user

    def extract_all(self):
        """
        Returns a mapping of drupal user ids to Django User pks.
        :return: dict
        """
        user_id_map = {}
        contributors = []
        for raw_user in self.data:
            user = UserExtractor._extract(raw_user)
            if user:
                user_id_map[user.drupal_uid] = user.pk
                contributors.append(Contributor(user=user, email=user.email))
        Contributor.objects.bulk_create(contributors)
        return user_id_map


class ProfileExtractor(Extractor):
    def extract_all(self, user_id_map, tag_id_map):
        for raw_profile in self.data:
            drupal_uid = raw_profile['uid']
            user_id = user_id_map.get(drupal_uid, -1)
            if user_id == -1:
                logger.warning("Drupal UID %s not found in user id map, skipping", drupal_uid)
                continue
            user = User.objects.get(pk=user_id)
            user.first_name = self.sanitize_name(get_first_field(raw_profile, 'field_profile2_firstname'))
            user.last_name = self.sanitize_name(get_first_field(raw_profile, 'field_profile2_lastname'))
            member_profile = user.member_profile
            member_profile.research_interests = get_first_field(raw_profile, 'field_profile2_research')
            raw_institutions = get_field(raw_profile, 'field_profile2_institutions')
            if raw_institutions:
                raw_institution = raw_institutions[0]
                institution, created = Institution.objects.get_or_create(name=raw_institution['title'],
                                                                         url=raw_institution['url'])
                member_profile.institution = institution
            member_profile.degrees = get_field_attributes(raw_profile, 'field_profile2_degrees') or []
            member_profile.personal_url = get_first_field(raw_profile, 'field_profile2_personal_link',
                                                          attribute_name='url')

            # crude aggregation of the wretched smorgasbord of incoming urls
            linkedin_url = get_first_field(raw_profile, 'field_profile2_linkedin_link',
                                           attribute_name='url')
            academia_edu_url = get_first_field(raw_profile, 'field_profile2_academiaedu_link',
                                               attribute_name='url')
            cv_url = get_first_field(raw_profile, 'field_profile2_cv_link', attribute_name='url')
            institutional_homepage_url = get_first_field(raw_profile, 'field_profile2_institution_link',
                                                         attribute_name='url')
            researchgate_url = get_first_field(raw_profile, 'field_profile2_researchgate_link',
                                               attribute_name='url')
            member_profile.professional_url = institutional_homepage_url \
                or researchgate_url \
                or academia_edu_url \
                or cv_url \
                or linkedin_url
            for url in ('professional_url', 'personal_url'):
                if len(getattr(member_profile, url, '')) > 200:
                    logger.warning("Ignoring overlong %s URL %s", url, getattr(member_profile, url))
                    setattr(member_profile, url, '')
            tags = flatten([tag_id_map[tid] for tid in
                            get_field_attributes(raw_profile, 'taxonomy_vocabulary_6', attribute_name='tid') if
                            tid in tag_id_map])
            member_profile.keywords.add(*tags)
            member_profile.save()
            user.save()
            if all([user.first_name, user.last_name]):
                Contributor.objects.filter(user=user).update(given_name=user.first_name, family_name=user.last_name)


class TaxonomyExtractor(Extractor):
    # DELIMITERS = (';', ',', '.')
    DELIMITER_REGEX = re.compile(r';|,|\.')

    def extract_all(self):
        tag_id_map = defaultdict(list)
        for raw_tag in self.data:
            if raw_tag['vocabulary_machine_name'] == 'vocabulary_6':
                raw_tag_name = raw_tag['name']
                # if the taxonomy was manually delimited by semicolons, commas, or periods and not split by Drupal
                # try, in that order, to split them
                tags = filter(lambda x: x.strip(), re.split(self.DELIMITER_REGEX, raw_tag_name))
                for t in tags:
                    sanitized_tag = self.sanitize(t, max_length=100)
                    tag, created = Tag.objects.get_or_create(name=sanitized_tag)
                    tag_id_map[raw_tag['tid']].append(sanitized_tag)
        return tag_id_map


class AuthorExtractor(Extractor):
    def _extract(self, raw_author):
        given_name = self.sanitize_name(get_first_field(raw_author, 'field_model_authorfirst', default=''))
        middle_name = self.sanitize_name(get_first_field(raw_author, 'field_model_authormiddle', default=''))
        family_name = self.sanitize_name(get_first_field(raw_author, 'field_model_authorlast', default=''))
        if any([given_name, middle_name, family_name]):
            try:
                contributor, created = Contributor.objects.get_or_create(
                    given_name=given_name,
                    family_name=family_name,
                    defaults={'middle_name': middle_name}
                )
            except Contributor.MultipleObjectsReturned:
                contributors = Contributor.objects.filter(given_name=given_name, family_name=family_name)
                logger.warning("XXX: multiple contributors (%s) found named [%s %s] %s", contributors,
                               given_name, family_name, middle_name)
                contributor = contributors.first()
                if contributors.filter(user__isnull=False).count() >= 1:
                    # first, try to pick first Contributor with an associated User
                    contributor = contributors.filter(user__isnull=False).first()
                elif contributors.exclude(email='').count() >= 1:
                    # no associated Users, grab first Contributor with an email
                    contributor = contributors.exclude(email='').first()
                else:
                    #
                    logger.warning("XXX: There are multiple users and contributors with this name. Picking first one.")
                contributor.middle_name = middle_name
                contributor.save()

            contributor.item_id = raw_author['item_id']
            return contributor
        return None

    def extract_all(self):
        author_id_map = {}
        for raw_author in self.data:
            c = self._extract(raw_author)
            if c:
                author_id_map[c.item_id] = c.pk
        return author_id_map


class ModelExtractor(Extractor):
    def _extract(self, raw_model, user_id_map, author_id_map):
        raw_author_ids = [raw_author['value'] for raw_author in get_field(raw_model, 'field_model_author')]
        author_ids = [author_id_map[raw_author_id] for raw_author_id in raw_author_ids]
        submitter_id = user_id_map[raw_model.get('uid')]
        if not author_ids:
            author_ids = [Contributor.objects.get(user__id=submitter_id).pk]
        with suppress_auto_now(Codebase, 'last_modified'):
            last_changed = to_datetime(raw_model['changed'])
            handle = get_first_field(raw_model, 'field_model_handle', default=None)
            peer_reviewed = self.int_to_bool(get_first_field(raw_model, 'field_model_certified', default=0))
            # set peer reviewed codebases as featured
            featured = self.int_to_bool(get_first_field(raw_model, 'field_model_featured', default=0)) or peer_reviewed
            code = Codebase.objects.create(
                title=raw_model['title'].strip(),
                description=self.sanitize_text(get_first_field(raw_model, field_name='body', default='')),
                summary=self.sanitize_text(
                    get_first_field(raw_model, field_name='body', attribute_name='summary', default=''),
                    max_length=500
                ),
                date_created=to_datetime(raw_model['created']),
                first_published_at=to_datetime(raw_model['created']),
                last_published_on=last_changed,
                last_modified=last_changed,
                doi=handle,
                uuid=raw_model['uuid'],
                is_replication=Extractor.int_to_bool(get_first_field(raw_model, 'field_model_replicated', default='0')),
                references_text=get_first_field(raw_model, 'field_model_reference', default=''),
                associated_publication_text=get_first_field(raw_model, 'field_model_publication_text', default=''),
                identifier=raw_model['nid'],
                submitter_id=submitter_id,
                featured=featured,
                peer_reviewed=peer_reviewed,
                live=self.int_to_bool(raw_model['status']),
            )
            code.author_ids = author_ids
            code.keyword_tids = get_field_attributes(raw_model, 'taxonomy_vocabulary_6', attribute_name='tid')
        return code

    def extract_all(self, user_id_map, tag_id_map, author_id_map):
        model_code_list = [self._extract(raw_model, user_id_map, author_id_map) for raw_model in self.data]
        model_id_map = {}

        for model_code in model_code_list:
            model_code.cached_contributors = []
            for idx, author_id in enumerate(model_code.author_ids):
                model_code.cached_contributors.append(
                    ReleaseContributor(contributor_id=author_id, index=idx)
                )
            # NOTE: some tids may have been converted to multiple tags due to splitting
            model_code.tags.add(*flatten([tag_id_map[tid] for tid in model_code.keyword_tids]))
            model_id_map[model_code.identifier] = model_code
        return model_id_map


class ModelVersionExtractor(Extractor):
    PROGRAMMING_LANGUAGES = [
        'other',
        'c',
        'c++',
        'java',
        'logo (variant)',
        'perl',
        'python',
    ]

    OS_LIST = [os[0] for os in OPERATING_SYSTEMS]

    def _extract(self, raw_model_version, model_id_map: Dict[str, Codebase]):
        model_nid = get_first_field(raw_model_version, 'field_modelversion_model', attribute_name='nid')
        platform_id = int(get_first_field(raw_model_version, 'field_modelversion_platform', default=0))
        license_id = int(get_first_field(raw_model_version, 'field_modelversion_license', default=0))
        version_number = int(get_first_field(raw_model_version, 'field_modelversion_number', default=1))
        platform = Platform.objects.get(pk=platform_id)
        codebase = model_id_map.get(model_nid)
        if codebase:
            release_notes = get_first_field(raw_model_version, 'body')
            language = ModelVersionExtractor.PROGRAMMING_LANGUAGES[int(
                get_first_field(raw_model_version, 'field_modelversion_language', default=0))
            ]
            language_version = get_first_field(raw_model_version, 'field_modelversion_language_ver', default='')

            dependencies = {
                'programming_language': {
                    'name': language,
                    'version': language_version,
                }
            }
            # FIXME: extract runconditions
            codebase_live = codebase._live[0]
            with suppress_auto_now([Codebase, CodebaseRelease], 'last_modified'):
                last_changed = to_datetime(raw_model_version['changed'])
                codebase_release = codebase.import_release(
                    release_notes=self.sanitize_text(release_notes),
                    date_created=to_datetime(raw_model_version['created']),
                    first_published_at=to_datetime(raw_model_version['created']),
                    # codebase releases do not have correct liveness values in the db dump so if containing codebase
                    # is private assume the release is as well
                    live=self.int_to_bool(raw_model_version['status']) and codebase_live,
                    last_modified=last_changed,
                    last_published_on=last_changed,
                    os=self.OS_LIST[int(get_first_field(raw_model_version, 'field_modelversion_os', default=0))],
                    license_id=license_id,
                    identifier=raw_model_version['vid'],
                    dependencies=dependencies,
                    submitter_id=codebase.submitter_id,
                    version_number="1.{}.0".format(version_number - 1),
                )
                # FIXME: if these do not exist in the DB, add them to the list of tags
                codebase_release.programming_languages.add(language)
                if language_version:
                    codebase_release.programming_languages.add(language_version)
                codebase_release.platforms.add(platform)
                if platform_id == 0:
                    # check for platform_ver and add to tags if it exists
                    platform_version = get_first_field(raw_model_version, 'field_modelversion_platform_ver')
                    if platform_version:
                        codebase_release.platform_tags.add(self.sanitize(platform_version))
                else:
                    codebase_release.platform_tags.add(platform.name)
                release_contributors = []
                # re-create new CodebaseContributors for each model version
                # do not modify codebase.contributors in place or it will overwrite previous version contributors
                for contributor in codebase.cached_contributors:
                    release_contributors.append(ReleaseContributor(
                        index=contributor.index,
                        contributor_id=contributor.contributor_id,
                        release_id=codebase_release.pk
                    ))
                ReleaseContributor.objects.bulk_create(release_contributors)
                codebase_release.save()
                return raw_model_version['nid'], codebase_release.id
        else:
            logger.warning("Unable to locate parent model nid %s for version %s", model_nid, raw_model_version['vid'])
            return None

    def extract_all(self, model_id_map: Dict[str, Codebase]):
        model_version_id_map = {}
        for raw_model_version in self.data:
            result = self._extract(raw_model_version, model_id_map)
            if result:
                drupal_id, pk = result
                model_version_id_map[drupal_id] = pk
        return model_version_id_map


class ValidationError(KeyError):
    pass


class DownloadCountExtractor:
    """
    Download data extracted the openabm website using

    ```
    SELECT id as nid, timestamp as date_created, download_count.uid, ip_address, referrer, node.type
    FROM openabm.download_count as download_count
    INNER JOIN openabm.node as node on node.nid = download_count.id
    INTO OUTFILE '/var/backups/DownloadCount.csv'
    FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\n';
    ```
    """

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_file(cls, file_path: str):
        with open(file_path, 'r') as f:
            return cls(list(csv.DictReader(f)))

    @staticmethod
    def _get_instance(raw_download, instance_id_map, field_name: str, message: str):
        drupal_id = raw_download[field_name]
        instance = instance_id_map.get(drupal_id)
        if instance is None:
            raise ValidationError(message.format(drupal_id))

        return instance

    @classmethod
    def _get_user_id(cls, raw_download, user_id_map):
        user = user_id_map.get(raw_download['uid'])
        if not user:
            logger.info("Unable to locate user with Drupal UID %s. Setting user NULL", raw_download['uid'])
        return user

    @classmethod
    def _get_codebase_release(cls, raw_download, model_version_id_map):
        codebase_release_id = cls._get_instance(raw_download, model_version_id_map, 'nid',
                                                "Unable to locate associated model version nid {}")
        return CodebaseRelease.objects.get(id=codebase_release_id)

    @classmethod
    def _get_codebase(cls, raw_download, model_id_map):
        return cls._get_instance(raw_download, model_id_map, 'nid',
                                 "Unable to locate associated model nid {}")

    def extract_all(self, model_id_map: Dict[str, int], model_version_id_map: Dict[str, int],
                    user_id_map: Dict[str, int]):

        downloads = []
        for raw_download in self.data:
            try:
                user_id = self._get_user_id(raw_download, user_id_map)
                """
                Some download counts in Drupal are at the Codebase level but now they are always at the CodebaseRelease 
                level. In order to match the new database structure assume that all codebase level downloads occurred 
                at the first release of the codebase
                """
                if raw_download['type'] == 'model':
                    codebase = self._get_codebase(raw_download, model_id_map)

                    codebase_release = codebase.releases.first()
                elif raw_download['type'] == 'modelversion':
                    codebase_release = self._get_codebase_release(raw_download, model_version_id_map)
                else:
                    raise ValidationError('Invalid node type %s', raw_download['type'])
                downloads.append(CodebaseReleaseDownload(
                    date_created=to_datetime(raw_download['date_created']),
                    user_id=user_id,
                    release=codebase_release,
                    ip_address=raw_download['ip_address'],
                    referrer=Extractor.sanitize(raw_download['referrer'], max_length=500))
                )
            except ValidationError as e:
                logger.exception(e)

        CodebaseReleaseDownload.objects.bulk_create(downloads)


class IDMapper:
    def __init__(self, author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map):
        self._maps = {
            Contributor: author_id_map,
            User: user_id_map,
            CodebaseTag: tag_id_map,
            Codebase: model_id_map,
            CodebaseRelease: model_version_id_map
        }

    def __getitem__(self, item):
        return self._maps[item]


def load_platforms():
    Platform.objects.all().delete()
    load_data(Platform, PLATFORMS)


def load_licenses():
    License.objects.all().delete()
    load_data(License, LICENSES)


def load_journals():
    Journal.objects.all().delete()
    load_data(Journal, JOURNALS)


def load_faq_entries():
    FaqEntry.objects.all().delete()
    load_data(FaqEntry, FAQ_ENTRIES)


def load(directory: str):
    # TODO: associate picture with profile
    user_extractor = UserExtractor.from_file(os.path.join(directory, "User.json"))
    profile_extractor = ProfileExtractor.from_file(os.path.join(directory, "Profile2.json"))
    author_extractor = AuthorExtractor.from_file(os.path.join(directory, "Author.json"))
    event_extractor = EventExtractor.from_file(os.path.join(directory, "Event.json"))
    job_extractor = JobExtractor.from_file(os.path.join(directory, "Forum.json"))
    model_extractor = ModelExtractor.from_file(os.path.join(directory, "Model.json"))
    model_version_extractor = ModelVersionExtractor.from_file(os.path.join(directory, "ModelVersion.json"))
    taxonomy_extractor = TaxonomyExtractor.from_file(os.path.join(directory, "Taxonomy.json"))

    download_extractor = DownloadCountExtractor.from_file(os.path.join(directory, "DownloadCount.csv"))

    load_licenses()

    load_platforms()

    load_journals()

    load_faq_entries()

    # extract Users first so that we have a remote chance of correlating Authors with Users
    user_id_map = user_extractor.extract_all()
    # extract Drupal taxonomy terms
    tag_id_map = taxonomy_extractor.extract_all()
    # profile extraction adds first name / last name and MemberProfile fields to Users.
    profile_extractor.extract_all(user_id_map, tag_id_map)
    # extract Codebase Authors, then try to correlate with existing Users
    author_id_map = author_extractor.extract_all()
    job_extractor.extract_all(user_id_map)
    event_extractor.extract_all(user_id_map)
    model_id_map = model_extractor.extract_all(user_id_map, tag_id_map, author_id_map)
    model_version_id_map = model_version_extractor.extract_all(model_id_map)
    download_extractor.extract_all(model_id_map, model_version_id_map, user_id_map)

    return IDMapper(author_id_map, user_id_map, tag_id_map, model_id_map, model_version_id_map)
