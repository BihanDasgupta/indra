"""This module contains functions for extracting statements from text using
first ChatGPT and then REACH."""
import argparse

import pandas as pd

from indra_gpt.api import run_openai_chat
from indra.sources import reach

from indra.statements.io import stmts_to_json_file

import json

JSON_Schema = [{
    "$schema": "http://json-schema.org/draft-06/schema#",
    "id": "http://www.indra.bio/schemas/statements.json",
    "definitions": {
        "ModCondition": {
            "type": "object",
            "description": "Mutation state of an amino acid position of an Agent.",
            "properties": {
                "mod_type": {
                    "type": "string",
                    "description": "The type of post-translational modification, e.g., 'phosphorylation'. Valid modification types currently include: 'phosphorylation', 'ubiquitination', 'sumoylation', 'hydroxylation', and 'acetylation'. If an invalid modification type is passed an InvalidModTypeError is raised."
                },
                "residue": {
                    "type": "string",
                    "description": "String indicating the modified amino acid, e.g., 'Y' or 'tyrosine'. If None, indicates that the residue at the modification site is unknown or unspecified."
                },
                "position": {
                    "type": "string",
                    "description": "String indicating the position of the modified amino acid, e.g., '202'. If None, indicates that the position is unknown or unspecified."
                },
                "is_modified": {
                    "type": "boolean",
                    "description": "Specifies whether the modification is present or absent. Setting the flag specifies that the Agent with the ModCondition is unmodified at the site."
                }
            },
            "required": ["mod_type", "is_modified"]
        },
        "MutCondition": {
            "type": "object",
            "description": "Mutation state of an amino acid position of an Agent.",
            "properties": {
                "position": {
                    "type": ["string", "null"],
                    "description": "Residue position of the mutation in the protein sequence."
                },
                "residue_from": {
                    "type": ["string", "null"],
                    "description": "Wild-type (unmodified) amino acid residue at the given position."
                },
                "residue_to": {
                    "type": ["string", "null"],
                    "description": "Amino acid at the position resulting from the mutation."
                }
            },
            "required": ["position", "residue_from", "residue_to"]
        },
        "ActivityCondition": {
            "type": "object",
            "description": "An active or inactive state of a protein.",
            "properties": {
                "activity_type": {
                    "type": "string",
                    "description": "The type of activity, e.g. 'kinase'. The basic, unspecified molecular activity is represented as 'activity'. Examples of other activity types are 'kinase', 'phosphatase', 'catalytic', 'transcription', etc."
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Specifies whether the given activity type is present or absent."
                }
            },
            "required": ["activity_type", "is_active"]
        },
        "BoundCondition": {
            "type": "object",
            "description": "Identify Agents bound (or not bound) to a given Agent in a given context.",
            "properties": {
                "agent": {
                    "$ref": "#/definitions/Agent"
                },
                "is_bound": {
                    "type": "boolean",
                    "description": "Specifies whether the given Agent is bound or unbound in the current context."
                }
            },
            "required": ["agent", "is_bound"]
        },
        "Agent": {
            "type": "object",
            "description": "A molecular entity, e.g., a protein.",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the agent, preferably a canonicalized name such as an HGNC gene name."
                },
                "mods": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/ModCondition"},
                    "description": "Modification state of the agent."
                },
                "mutations": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/MutCondition"},
                    "description": "Amino acid mutations of the agent."
                },
                "bound_conditions": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/BoundCondition"},
                    "description": "Other agents bound to the agent in this context."
                },
                "activity": {
                    "$ref": "#/definitions/ActivityCondition",
                    "description":"Activity of the agent."
                },
                "location": {
                    "type": "string",
                    "description": "Cellular location of the agent. Must be a valid name (e.g. 'nucleus') or identifier (e.g. 'GO:0005634')for a GO cellular compartment."
                },
                "db_refs": {
                    "type": "object",
                    "description": "Dictionary of database identifiers associated with this agent."
                },
                "sbo": {
                    "type": "string",
                    "description": "Role of this agent in the systems biology ontology"
                }
            },
            "required": ["name", "db_refs"]
        },
        "Concept": {
            "type": "object",
            "description": "A concept/entity of interest that is the argument of a Statement",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the concept, possibly a canonicalized name."
                },
                "db_refs": {
                    "type": "object",
                    "description": "Dictionary of database identifiers associated with this concept."
                }
            },
            "required": ["name", "db_refs"]
        },
        "Context": {
            "type": "object",
            "description": "The context in which a given Statement was reported.",
            "properties": {
                "type": {
                    "type": "string",
                    "pattern": "^((bio)|(world))$",
                    "description": "Either 'world' or 'bio', depending on the type of context being repersented."
                }
            }
        },
        "BioContext": {
            "type": "object",
            "description": "The biological context of a Statement.",
            "properties": {
                "type": {
                    "type": "string",
                    "pattern": "^bio$",
                    "description": "The type of context, in this case 'bio'."
                },
                "location": {
                    "$ref": "#/definitions/RefContext",
                    "description": "Cellular location, typically a sub-cellular compartment."
                },
                "cell_line": {
                    "$ref": "#/definitions/RefContext",
                    "description": "Cell line context, e.g., a specific cell line, like BT20."
                },
                "cell_type": {
                    "$ref": "#/definitions/RefContext",
                    "description": "Cell type context, broader than a cell line, like macrophage."
                },
                "organ": {
                    "$ref": "#/definitions/RefContext",
                    "description": "Organ context."
                },
                "disease": {
                    "$ref": "#/definitions/RefContext",
                    "description": "Disease context."
                },
                "species": {
                    "$ref": "#/definitions/RefContext",
                    "description": "Species context."
                }
            }
        },
        "WorldContext": {
            "type": "object",
            "description": "The temporal and spatial context of a Statement.",
            "properties": {
                "type": {
                    "type": "string",
                    "pattern": "^world$",
                    "description": "The type of context, in this case 'world'."
                },
                "time": {
                    "$ref": "#/definitions/TimeContext",
                    "description": "The temporal context of a Statement."
                },
                "geo_location": {
                    "$ref": "#/definitions/RefContext",
                    "description": "The geographical context of a Statement."
                }
            }
        },
        "TimeContext": {
            "type": "object",
            "description": "Represents a temporal context.",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text associated with the temporal context."
                },
                "start": {
                    "type": "string",
                    "description": "The start time of the temporal context."
                },
                "end": {
                    "type": "string",
                    "description": "The end time of the temporal context."
                },
                "duration": {
                    "type": "string",
                    "description": "The duration of the temporal context."
                }
            }
        },
        "RefContext": {
            "type": "object",
            "description": "Represents a context identified by name and grounding references.",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name associated with the context."
                },
                "db_refs": {
                    "type": "object",
                    "description": "Dictionary of database identifiers associated with this context."
                }
            }
        },
        "Evidence": {
            "type": "object",
            "description": "Container for evidence supporting a given statement.",
            "properties": {
                "source_api": {
                    "type": "string",
                    "description": "String identifying the INDRA API used to capture the statement, e.g., 'trips', 'biopax', 'bel'."
                },
                "pmid": {
                    "type": "string",
                    "description": "String indicating the Pubmed ID of the source of the statement."
                },
                "source_id": {
                    "type": "string",
                    "description": "For statements drawn from databases, ID of the database entity corresponding to the statement."
                },
                "text": {
                    "type": "string",
                    "description": "Natural language text supporting the statement."
                },
                "annotations": {
                    "type": "object",
                    "description": "Dictionary containing additional information on the context of the statement, e.g., species, cell line, tissue type, etc. The entries may vary depending on the source of the information."
                },
                "epistemics": {
                    "type": "object",
                    "description": "A dictionary describing various forms of epistemic certainty associated with the statement."
                }
            }
        },
        "Statement": {
            "type": "object",
            "description": "All statement types, below, may have these fields and 'inherit' from this schema",
            "properties": {
                "evidence": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/Evidence"
                    }
                },
                "id": {
                    "type": "string",
                    "description": "Statement UUID"
                },
                "supports": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "supported_by": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": ["id"]
        },
        "Modification": {
            "description": "Statement representing the modification of a protein.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^((Phosphorylation)|(Dephosphorylation)|(Ubiquitination)|(Deubiquitination)|(Sumoylation)|(Desumoylation)|(Hydroxylation)|(Dehydroxylation)|(Acetylation)|(Deacetylation)|(Glycosylation)|(Deglycosylation)|(Farnesylation)|(Defarnesylation)|(Geranylgeranylation)|(Degeranylgeranylation)|(Palmitoylation)|(Depalmitoylation)|(Myristoylation)|(Demyristoylation)|(Ribosylation)|(Deribosylation)|(Methylation)|(Demethylation))$",
                            "description": "The type of the statement"
                        },
                        "enz": {
                            "$ref": "#/definitions/Agent",
                            "description": "The enzyme involved in the modification."
                        },
                        "sub": {
                            "$ref": "#/definitions/Agent",
                            "description": "The substrate of the modification."
                        },
                        "residue": {
                            "type": "string",
                            "description": "The amino acid residue being modified, or None if it is unknown or unspecified."
                        },
                        "position": {
                            "type": "string",
                            "description": "The position of the modified amino acid, or None if it is unknown or unspecified."
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "SelfModification": {
            "description": "Statement representing the self-modification of a protein.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^((Autophosphorylation)|(Transphosphorylation))$",
                            "description": "The type of the statement"
                        },
                        "enz": {
                            "$ref": "#/definitions/Agent",
                            "description": "The enzyme involved in the modification."
                        },
                        "residue": {
                            "type": "string",
                            "description": "The amino acid residue being modified, or None if it is unknown or unspecified."
                        },
                        "position": {
                            "type": "string",
                            "description": "The position of the modified amino acid, or None if it is unknown or unspecified."
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "RegulateActivity": {
            "description": "Regulation of activity (such as activation and inhibition)",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^((Activation)|(Inhibition))$",
                            "description": "The type of the statement"
                        },
                        "subj": {
                            "$ref": "#/definitions/Agent",
                            "description": "The agent responsible for the change in activity, i.e., the 'upstream' node."
                        },
                        "obj": {
                            "$ref": "#/definitions/Agent",
                            "description": "The agent whose activity is influenced by the subject, i.e., the 'downstream' node."
                        },
                        "obj_activity": {
                            "type": "string",
                            "description": "The activity of the obj Agent that is affected, e.g., its 'kinase' activity."
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "ActiveForm": {
            "description": "Specifies conditions causing an Agent to be active or inactive. Types of conditions influencing a specific type of biochemical activity can include modifications, bound Agents, and mutations.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^ActiveForm$",
                            "description": "The type of the statement"
                        },
                        "agent": {
                            "$ref": "#/definitions/Agent",
                            "description": "The Agent in a particular active or inactive state. The sets of ModConditions, BoundConditions, and MutConditions on the given Agent instance indicate the relevant conditions."
                        },
                        "activity": {
                            "type": "string",
                            "description": "The type of activity influenced by the given set of conditions, e.g., 'kinase'."
                        },
                        "is_active": {
                            "type": "boolean",
                            "description": "Whether the conditions are activating (True) or inactivating (False)."
                        }
                    },
                    "required": ["type", "agent", "activity"]
                }
            ]
        },
        "Gef": {
            "description": "Exchange of GTP for GDP on a small GTPase protein mediated by a GEF. Represents the generic process by which a guanosine exchange factor (GEF) catalyzes nucleotide exchange on a GTPase protein.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^Gef$",
                            "description": "The type of the statement"
                        },
                        "gef": {
                            "$ref": "#/definitions/Agent",
                            "description": "The guanosine exchange factor."
                        },
                        "ras": {
                            "$ref": "#/definitions/Agent",
                            "description": "The GTPase protein."
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "Gap": {
            "description": "Acceleration of a GTPase protein's GTP hydrolysis rate by a GAP. Represents the generic process by which a GTPase activating protein (GAP) catalyzes GTP hydrolysis by a particular small GTPase protein.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^Gap$",
                            "description": "The type of the statement"
                        },
                        "gap": {
                            "$ref": "#/definitions/Agent",
                            "description": "The GTPase activating protein."
                        },
                        "ras": {
                            "$ref": "#/definitions/Agent",
                            "description": "The GTPase protein."
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "Complex": {
            "description": "A set of proteins observed to be in a complex.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^((Complex)|(Association))$",
                            "description": "The type of the statement"
                        },
                        "members": {
                            "type": "array",
                            "items": {
                                "$ref": "#/definitions/Agent"
                            }
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "Association": {
            "description": "A set of unordered concepts that are associated with each other.",
            "allOf": [
                {
                    "$ref": "#/definitions/Complex"
                }
            ]
        },
        "Translocation": {
            "description": "The translocation of a molecular agent from one location to another.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^Translocation$",
                            "description": "The type of the statement"
                        },
                        "agent": {
                            "$ref": "#/definitions/Agent",
                            "description": "The agent which translocates."
                        },
                        "from_location": {
                            "type": "string",
                            "description": "The location from which the agent translocates. This must be a valid GO cellular component name (e.g. 'cytoplasm') or ID (e.g. 'GO:0005737')."
                        },
                        "to_location": {
                            "type": "string",
                            "description": "The location to which the agent translocates. This must be a valid GO cellular component name or ID."
                        }
                    },
                    "required": ["type", "agent"]
                }
            ]
        },
        "RegulateAmount": {
            "description": "Represents directed, two-element interactions.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^((IncreaseAmount)|(DecreaseAmount))$"
                        },
                        "subj": {
                            "$ref": "#/definitions/Agent",
                            "description": "The mediating protein"
                        },
                        "obj": {
                            "$ref": "#/definitions/Agent",
                            "description": "The affected protein"
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "Influence": {
            "description": "A causal influence between two events.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^Influence$"
                        },
                        "subj": {
                            "$ref": "#/definitions/Event",
                            "description": "The event which acts as the influencer."
                        },
                        "obj": {
                            "$ref": "#/definitions/Event",
                            "description": "The event which acts as the influencee"
                        }
                    },
                    "required": ["type"]
                }
            ]
        },
        "Event": {
            "description": "An event over a concept of interest.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^Event$"
                        },
                        "concept": {
                            "$ref": "#/definitions/Concept",
                            "description": "The concept which the event happens to."
                        },
                        "delta": {
                            "type": ["object", "null"],
                            "description": "A dictionary specifying the polarity and adjactives of change in concept."
                        },
                        "context": {
                            "$ref": "#/definitions/Context",
                            "description": "The context associated with the event"
                        }
                    },
                    "required": ["type", "concept"]
                }
            ]
        },
        "Conversion": {
            "description": "Conversion of molecular species mediated by a controller protein.",
            "allOf": [
                {
                    "$ref": "#/definitions/Statement"
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "pattern": "^Conversion$"
                        },
                        "subj": {
                            "$ref": "#/definitions/Agent",
                            "description": "The protein mediating the conversion."
                        },
                        "obj_from": {
                            "type": "array",
                            "items": {
                                "$ref": "#/definitions/Agent"
                            },
                            "description": "The list of molecular species being consumed by the conversion."
                        },
                        "obj_to": {
                            "type": "array",
                            "items": {
                                "$ref": "#/definitions/Agent"
                            },
                            "description": "The list of molecular species being created by the conversion."
                        }
                    },
                    "required": ["type"]
                }
            ]
        }
    },

    "type": "array",
    "items": {
        "anyOf": [
            {"$ref": "#/definitions/RegulateActivity"},
            {"$ref": "#/definitions/Modification"},
            {"$ref": "#/definitions/SelfModification"},
            {"$ref": "#/definitions/ActiveForm"},
            {"$ref": "#/definitions/Gef"},
            {"$ref": "#/definitions/Gap"},
            {"$ref": "#/definitions/Complex"},
            {"$ref": "#/definitions/Association"},
            {"$ref": "#/definitions/Translocation"},
            {"$ref": "#/definitions/RegulateAmount"},
            {"$ref": "#/definitions/Influence"},
            {"$ref": "#/definitions/Conversion"},
            {"$ref": "#/definitions/Event"}
        ]
    }
}]
JSON = str(JSON_Schema)

def run_chat_gpt_on_ev_text(ev_text: str, examples, debug=False) -> str:
    """ takes in ev_text and returns english statement

    Parameters
    ----------
    ev_text :
        the text to generate an english statement from
    examples :
        a list of lists where the first item is the english statement and the
        second item is the evidence text that supports the english statement

    Returns
    -------
    :
        english statement from ChatGPT
    """

    prompt_templ = '1. Read the following data: \n' + JSON + '\n' + \
                   '2. Extract the relation from this sentence using the ' \
                   'data above:  \n"{' \
                   'prompt}"'
    history = [
        {"role": "user",
         "content": prompt_templ.format(prompt=examples[0][1])},
        {"role": "assistant",
         "content": examples[0][0]},
        {"role": "user",
         "content": prompt_templ.format(prompt=examples[1][1])},
        {"role": "assistant",
         "content": examples[1][0]}
    ]

    prompt = prompt_templ.format(prompt=ev_text)

    chat_gpt_english = run_openai_chat(prompt, chat_history=history,
                                       max_tokens=25, strip=False, debug=debug)
    return chat_gpt_english


def main(training_df, n_statements=10, debug=False):
    # Ensure we only use statements curated as correct
    training_df = training_df[training_df['tag'] == 'correct']

    # Loop over the training data and extract english statements from the

    # chatGPT output and save to a list
    gpt_english_statements = []
    statistics = []

    for item in training_df[['pa_hash','source_hash','text','english']].values:
        pa_hash, source_hash,text, english = item
        examples = training_df[['english','text']].sample(2).values
        gpt_english = run_chat_gpt_on_ev_text(text,examples,debug=debug)
        gpt_english_statements.append(gpt_english)
        statistics.append((
            pa_hash, source_hash, text, english, gpt_english
        ))
        if len(gpt_english_statements)==n_statements:
            break

    # Concatenate the chatGPT output to a single string with one english
    # statement per line
    gpt_englsh_statements_str = '\n'.join(gpt_english_statements)

    # Run REACH on the chatGPT output
    reach_processor = reach.process_text(gpt_englsh_statements_str,
                                         url=reach.local_text_url)

    # Compare with original statements and check if ChatGPT+REACH
    # extracted the same statements as the original statements

    return reach_processor, statistics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--training_df', type=str, required=True)
    parser.add_argument('--n_statements', type=int, default=10)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    training_data_df = pd.read_csv(args.training_df, sep='\t')

    reach_processor, statistics = main(training_data_df, args.n_statements,
                                       debug=args.debug)
    # save statements in reach_processor in json or pickle into a file
    # save the statistics
    # change the prompt so ChatGPT writes something like the statement we want

# 'reach_processor'+'_('+prompt+')_'+'.json'

    #with open('reach_processor.json', 'w') as f:
       #json.dump(reach_processor, f)

    stmts_to_json_file(stmts=reach_processor.statements,
                       fname='JSON_schema_statements_.json')
    #stmts_to_json_file(stmts=statistics,
                       #fname='statistics.json')

    with open('statistics_JSON_schema.json', 'w') as f:
        json.dump(statistics, f)

    print("Done.")
    #print(JSON)
