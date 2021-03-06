import argparse
import json
import sys
import os
from urllib.parse import urlparse
from pySBOLx.pySBOLx import XDocument
from synbiohub_adapter.upload_sbol import SynBioHub
from SPARQLWrapper import SPARQLWrapper, JSON

SD2_NS = 'http://hub.sd2e.org/user/sd2e'
SD2S_NS = 'https://hub.sd2e.org/user/sd2e'
SD2_DESIGN_ID = 'design'
SD2_EXP_ID = 'experiment'
SD2_DESIGN_NAME = 'SD2 Designs'
SD2_EXP_NAME = 'SD2 Experiments'
SD2_DESIGN_NS = ''.join([SD2_NS, '/', SD2_DESIGN_ID])
SD2_EXP_NS = ''.join([SD2_NS, '/', SD2_EXP_ID])
SD2S_DESIGN_NS = ''.join([SD2S_NS, '/', SD2_DESIGN_ID])
SD2S_EXP_NS = ''.join([SD2S_NS, '/', SD2_EXP_ID])
SD2_EXP_COLLECTION = 'https://hub.sd2e.org/user/sd2e/experiment/experiment_collection/1'

def load_alnum_id(id_data):
    if id_data.replace('_', '').replace('-', '').replace(':', '').isalnum():
        return id_data.replace('-', '_').replace(':', '')
    else:
        parsed_uri = urlparse(id_data)

        if parsed_uri.hostname == 'hub.sd2e.org':
            return parsed_uri.path.split('/')[-2]
        else:
            path = parsed_uri.path[1:].replace('/', '_').replace('-', '_').replace('.', '_')

            fragment = parsed_uri.fragment.replace('/', '_').replace('-', '_').replace('.', '_')

            if len(path) > 0 and len(fragment) > 0:
                return ''.join([path, '_', fragment])
            elif len(path) > 0:
                return path
            else:
                return fragment

def load_build_activity(src_entity_keys, doc, operator, replicate_id, act_dict, act_name=None, act_desc=None, dest_sample_key=None, custom=[]):
    src_entities = []

    temp_act_dict = {}

    for src_entity_key in src_entity_keys:
        if isinstance(src_entity_key, str):
            try:
                if src_entity_key not in temp_act_dict:
                    src_entities.append(act_dict[src_entity_key])
                    temp_act_dict[src_entity_key] = src_entities[-1]
            except:
                src_entities.append(load_sample(src_entity_key, doc))

    if dest_sample_key is None:
        act = doc.create_activity(operator, replicate_id, src_entities, act_name, act_desc, custom)

        act_dict[src_entity_key] = act
    else:
        dest_sample = load_sample(dest_sample_key, doc)

        act = doc.create_activity(operator, replicate_id, src_entities, act_name, act_desc, custom, dest_sample)

def load_src_dest_build_activity(sample_data, doc, operator, replicate_id, act_dict, act_name=None, act_desc=None):
    src_sample_data = load_src_sample_data(sample_data)

    dest_sample_data = load_dest_sample_data(sample_data)

    if isinstance(src_sample_data, str) and isinstance(dest_sample_data, str):
        load_build_activity([src_sample_data], doc, operator, replicate_id, act_dict, act_name, act_desc, dest_sample_data)
    elif isinstance(src_sample_data, str):
        for dest_sample_datum in dest_sample_data:
            load_build_activity([src_sample_data], doc, operator, replicate_id, act_dict, act_name, act_desc, load_dest_sample_key(dest_sample_datum))
    elif isinstance(dest_sample_data, str):
        src_sample_keys = []
        for src_sample_datum in src_sample_data:
            src_sample_keys.append(load_src_sample_key(src_sample_datum))
        load_build_activity(src_sample_keys, doc, operator, replicate_id, act_dict, act_name, act_desc, dest_sample_data)
    else:
        src_sample_keys = []
        for src_sample_datum in src_sample_data:
            src_sample_keys.append(load_src_sample_key(src_sample_datum))
        for dest_sample_datum in dest_sample_data:
            load_build_activity(src_sample_keys, doc, operator, replicate_id, act_dict, act_name, act_desc, load_dest_sample_key(dest_sample_datum))

def load_operator_activities(operator_data, doc, act_dict, om):
    operator = operator_data['type'].replace('-', '_')
    replicate_id = repr(operator_data['id'])

    try:
        act_name = operator_data['name']
    except:
        act_name = None
    try:
        act_desc = operator_data['description']
    except:
        act_desc = None

    sample_data = load_sample_data(operator_data)

    for sample_datum in sample_data:
        try:
            load_src_dest_build_activity(sample_datum, doc, operator, replicate_id, act_dict, act_name, act_desc)
        except:
            load_build_activity([load_src_sample_key(sample_datum)], doc, operator, replicate_id, act_dict, act_name, act_desc)

def load_channels(operator_data):
    channel_data = operator_data['channels']

    channels = []

    for channel_datum in channel_data:
        channel = {}
        channel['display_id'] = load_alnum_id(channel_datum.calibration_file)
        channel['calibration_file'] = channel_datum.calibration_file
        channel['name'] = channel_datum.name

    return channels

def load_test_activity(operator_data, doc, exp_data_dict, act_dict):
    operator = operator_data['type'].replace('-', '_')
    replicate_id = repr(operator_data['id'])

    if operator == 'uploadData':
        entity_data = operator_data['samples']
    else:
        entity_data = load_measurement_data(operator_data)

    try:
        act_name = operator_data['name']
    except:
        act_name = None
    try:
        act_desc = operator_data['description']
    except:
        act_desc = None

    custom = []
    try:
        custom.append(operator_data['manifest'])
        custom.append('manifest')
    except:
        pass
    try:
        custom.append(operator_data['instrument_configuration'])
        custom.append('instrument_configuration')
    except:
        pass

    try:
        channels = load_channels(operator_data)
    except:
        channels = []

    for entity_datum in entity_data:
        src_samples = []
        src_sample_keys = []

        src_sample_data = load_src_sample_data(entity_datum)

        if isinstance(src_sample_data, str):
            try:
                src_samples.append(act_dict[src_sample_data])
            except:
                src_samples.append(load_sample(src_sample_data, doc))
            src_sample_keys.append(src_sample_data)
        else:
            for src_sample_datum in src_sample_data:
                src_sample_key = load_src_sample_key(src_sample_datum)
                try:
                    src_samples.append(act_dict[src_sample_key])
                except:
                    src_samples.append(load_sample(src_sample_key, doc))
                src_sample_keys.append(src_sample_key)

        dest_exp_data = exp_data_dict[repr(load_file_paths(entity_datum))]

        for i in range(0, len(src_samples)):
            if len(channels) > 0:
                test_act = doc.create_flow_cytometry_activity(operator, '_'.join([replicate_id, repr(i)]), channels, [src_samples[i]], act_name, act_desc, custom, dest_exp_data)
            else:
                test_act = doc.create_activity(operator, '_'.join([replicate_id, repr(i)]), [src_samples[i]], act_name, act_desc, custom, dest_exp_data)

            act_dict[src_sample_keys[i]] = test_act

def load_step_activities(step_data, doc, exp_data_dict, act_dict, om):
    operator_data = step_data['operator']

    fail_count = 0

    try:
        load_operator_activities(operator_data, doc, act_dict, om)
    except:
        fail_count = fail_count + 1

    try:
        load_test_activity(operator_data, doc, exp_data_dict, act_dict)
    except:
        fail_count = fail_count + 1

    assert fail_count < 2

def load_src_sample_key(sample_data):
    try:
        sample_key = sample_data['source']
    except:
        try:
            sample_key = sample_data['sample']
        except:
            sample_key = sample_data

    return sample_key

def load_dest_sample_key(sample_data):
    try:
        sample_key = sample_data['dest']
    except:
        try:
            sample_key = sample_data['sample']
        except:
            sample_key = sample_data

    return sample_key

def load_sample(sample_key, doc, condition=None, src_samples=[], measures=[]):
    if sample_key.startswith(SD2S_DESIGN_NS):

        print(sample_key)

        return sample_key
    else:
        sample_id = load_alnum_id(sample_key)

        print(sample_id)

        sam = doc.create_sample(sample_id, condition, src_samples, measures)

        return sam

def load_src_sample_data(sample_data):
    try:
        src_sample_data = sample_data['sources']
    except:
        try:
            src_sample_data = sample_data['source']['sample']
        except:
            try:
                src_sample_data = sample_data['source']
            except:
                try:
                    src_sample_data = sample_data['sample']['source']
                except:
                    try:
                        src_sample_data = sample_data['resource']
                    except:
                        src_sample_data = sample_data['src']

    return src_sample_data

def load_dest_sample_data(sample_data):
    try:
        dest_sample_data = sample_data['destinations']
    except:
        try:
            dest_sample_data = sample_data['destination']['sample']
        except:
            try:
                dest_sample_data = sample_data['destination']
            except:
                try:
                    dest_sample_data = sample_data['sample']['destination']
                except:
                    try:
                        src_sample_data = sample_data['resource']
                        dest_sample_data = sample_data['sample']
                    except:
                        try:
                            dest_sample_data = sample_data['dests']
                        except:
                            dest_sample_data = sample_data['dest'] 

    return dest_sample_data

def load_src_samples(sample_data, doc):
    src_samples = []

    src_sample_data = load_src_sample_data(sample_data)

    if isinstance(src_sample_data, str):
        src_samples.append(load_sample(src_sample_data, doc))
    else:
        for src_sample_datum in src_sample_data:
            src_samples.append(load_sample(load_src_sample_key(src_sample_datum), doc))

    return src_samples

def load_dest_samples(sample_data, doc, src_samples, om, condition=None, measures=[]):
    dest_sample_data = load_dest_sample_data(sample_data)

    if isinstance(dest_sample_data, str):
        load_sample(dest_sample_data, doc, condition, src_samples, measures)
    else:
        for dest_sample_datum in dest_sample_data:
            try:
                local_measures = load_sample_attributes(dest_sample_datum, doc, om)
            except:
                local_measures = []
            local_measures.extend(measures)

            load_sample(load_dest_sample_key(dest_sample_datum), doc, condition, src_samples, local_measures)
        
def load_src_dest_samples(sample_data, doc, om, condition=None, measures=[]):
    src_samples = load_src_samples(sample_data, doc)

    load_dest_samples(sample_data, doc, src_samples, om, condition, measures)

def load_strains(condition_data, doc):
    strain_id = load_alnum_id(condition_data['strain'])

    return [doc.create_strain(strain_id, strain_id)]

def load_plasmids(condition_data, doc):
    plasmids = []

    for plasmid_data in condition_data['plasmids']:
        if isinstance(plasmid_data, str):
            plasmid_id = load_alnum_id(plasmid_data)

            plasmids.append([doc.create_plasmid(plasmid_id, plasmid_id)])
        else:
            sub_plasmids = []

            for plasmid_datum in plasmid_data:
                plasmid_id = load_alnum_id(plasmid_datum)

                sub_plasmids.append(doc.create_plasmid(plasmid_id, plasmid_id))

            plasmids.append(sub_plasmids)

    return plasmids

def load_unit(entity_data, doc, om):
    try:
        return doc.create_unit(om, entity_data['units'])
    except:
        name = entity_data.split(':')[1]

        return doc.create_unit(om=om, name=name)

def load_inducers(condition_data, doc, om, measures):
    inducer_data = condition_data['inducer']

    inducer_id = load_alnum_id(inducer_data['compound'])

    try:
        unit = load_unit(inducer_data, doc, om)
        measures[inducer_id] = {'id': None, 'mag': float(inducer_data['amount']), 'unit': unit}
    except:
        measures[inducer_id] = {'id': None, 'mag': float(inducer_data['amount']), 'unit': None}

    return [doc.create_inducer(inducer_id, inducer_id)]

def load_condition(condition_data, doc, om, plasmid=None):
    try:
        src_samples = load_src_samples(condition_data, doc)
    except:
        return None

    built = []

    for src_sample in src_samples:
        if isinstance(src_sample, str):
            built.append(src_sample)

    try:
        devices = load_strains(condition_data, doc)
    except:
        devices = []
    if plasmid is not None:
        if isinstance(plasmid, str):
            devices.append(plasmid)
        else:
            for plasm in plasmid:
                devices.append(plasm)

    measures = {}
    try:
        inputs = load_inducers(condition_data, doc, om, measures)
    except:
        inputs = []

    if len(built) + len(devices) + len(inputs) > 1:
        sub_systems = []
        for bu in built:
            try:
                devices.append(doc.get_device(bu))
            except:
                try:
                    sub_systems.append(doc.get_system(bu))
                except:
                    return None
        return doc.create_system(devices, sub_systems, inputs, measures)
    elif len(built) == 1:
        return built[0]
    elif len(devices) == 1:
        return devices[0]
    elif len(inputs) == 1:
        return inputs[0]
    else:
        return None

def load_file_paths(entity_data):
    try:
        file_paths = entity_data['files']
    except:
        try:
            file_paths = entity_data['uris']
        except:
            try:
                file_paths = entity_data['file']
            except:
                try:
                    file_paths = entity_data['uri']
                except:
                    file_paths = entity_data['dest']

    if isinstance(file_paths, str):
        return [file_paths]
    else:
        return file_paths

def load_measurement_data(operator_data):
    try:
        measure_data = operator_data['measurements']
    except:
        measure_data = operator_data['measure']

    return measure_data

def load_experimental_data(operator_data, doc, replicate_id, exp, exp_data_dict):
    operator = operator_data['type'].replace('-', '_')

    if operator == 'uploadData':
        entity_data = operator_data['samples']
    else:
        entity_data = load_measurement_data(operator_data)

    i = 0 

    for entity_datum in entity_data:
        samples = load_src_samples(entity_datum, doc)

        file_paths = load_file_paths(entity_datum)

        attachs = []

        for file_path in file_paths:
            attach_id = load_alnum_id(file_path)

            attachs.append(doc.create_attachment(display_id=attach_id, source=file_path, name=attach_id))

        file_key = repr(file_paths)

        if file_key not in exp_data_dict:
            exp_data_dict[file_key] = doc.create_experimental_data(attachs, samples, '_'.join([replicate_id, repr(i)]))
            
            exp.experimentalData.add(exp_data_dict[file_key].identity.replace('http', 'https'))

            i = i + 1

def load_sample_data(operator_data):
    try:
        entity_data = operator_data['transformations']
    except:
        try:
            entity_data = operator_data['samples']

            operator = operator_data['type'].replace('-', '_')

            assert operator != 'uploadData'
        except:
            try:
                entity_data = operator_data['transfer']
            except:
                try:
                    entity_data = operator_data['distribute']
                except:
                    entity_data = operator_data['transform']

    return entity_data

def load_sample_measures(sample_data, doc, measure_ids, om):
    measures = []

    for measure_id in measure_ids:
        try:
            measure_data = sample_data[measure_id]

            if isinstance(measure_data, str):
                mag = measure_data.split(':')[0]
                try:
                    unit = load_unit(measure_data, doc, om)
                    measures.append({'id': measure_id, 'mag': float(mag), 'unit': unit})
                except:
                    measures.append({'id': measure_id, 'mag': float(mag), 'unit': None})
            else:
                measures.append({'id': measure_id, 'mag': measure_data, 'unit': None})
        except:
            pass

    return measures

def load_sample_attributes(sample_data, doc, om):
    attribute_data = sample_data['attribute']

    attributes = []

    for key in attribute_data.keys():
        if isinstance(attribute_data[key], str):
            mag = attribute_data[key].split(':')[0]
            try:
                unit = load_unit(attribute_data[key], doc, om)
                attributes.append({'id': key, 'mag': float(mag), 'unit': unit})
            except:
                attributes.append({'id': key, 'mag': float(mag), 'unit': None})
        else:
            attributes.append({'id': key, 'mag': attribute_data[key], 'unit': None})

    return attributes

def load_operator_samples(operator_data, doc, om):
    sample_data = load_sample_data(operator_data)

    try:
        plasmids = load_plasmids(operator_data, doc)
    except:
        plasmids = []

    for i in range(0, len(sample_data)):
        if i < len(plasmids):
            condition = load_condition(sample_data[i], doc, om, plasmids[i])
        else:
            condition = load_condition(sample_data[i], doc, om)

        measures = load_sample_measures(sample_data[i], doc, ['od600', 'volume'], om)

        try:
            load_src_dest_samples(sample_data[i], doc, om, condition, measures)
        except:
            load_sample(load_src_sample_key(sample_data[i]), doc, condition)

def load_step_entities(step_data, doc, exp, exp_data_dict, om):
    operator_data = step_data['operator']

    fail_count = 0

    try:
        load_operator_samples(operator_data, doc, om)
    except:
        fail_count = fail_count + 1

    try:
        load_experimental_data(operator_data, doc, repr(step_data['id']), exp, exp_data_dict)
    except:
        fail_count = fail_count + 1

    assert fail_count < 2

def load_experimental_intent(plan_data, doc, exp, exp_vars, out_vars):
    intent_data = plan_data['intent']

    exp_design = doc.create_experimental_design(load_alnum_id(plan_data['id']) + '_design')

    for dv_data in intent_data['diagnostic-variables']:
        try:
            doc.create_diagnostic_variable(exp_design=exp_design, display_id=load_alnum_id(dv_data['uri']), name=dv_data['name'], definition=dv_data['uri'])
        except:
            doc.create_diagnostic_variable(exp_design, load_alnum_id(dv_data['name']), dv_data['name'])

    for ev_data in intent_data['experimental-variables']:
        try:
            exp_vars.append(doc.create_experimental_variable(exp_design=exp_design, display_id=load_alnum_id(ev_data['uri']), name=ev_data['name'], definition=ev_data['uri']))
        except:
            exp_vars.append(doc.create_experimental_variable(exp_design, load_alnum_id(ev_data['name']), ev_data['name']))

    for ov_data in intent_data['outcome-variables']:
        try:
            out_vars.append(doc.create_outcome_variable(exp_design=exp_design, display_id=load_alnum_id(ov_data['uri']), name=ov_data['name'], definition=ov_data['uri']))
        except:
            out_vars.append(doc.create_outcome_variable(exp_design, load_alnum_id(ov_data['name']), ov_data['name']))

    exp.experimentalDesign.add(exp_design.identity.replace('http', 'https'))

    return exp_design

def load_truth_table(plan_data, doc, exp_design, exp_vars, out_vars):
    intent_data = plan_data['intent']
    table_data = intent_data['truth-table']
    input_data = table_data['input']

    plan_id = load_alnum_id(plan_data['id'])

    exp_conditions = []
    for i in range(0, len(input_data)):
        condition_id = 'condition_' + repr(i + 1)
        exp_condition = doc.create_experimental_condition(exp_design=exp_design, display_id=condition_id, definition=input_data[i]['strain'])
        exp_conditions.append(exp_condition)

        exp_var_data = input_data[i]['experimental-variables']
        for j in range(0, len(exp_var_data)):
            input_id = 'input_' + repr(j + 1)
            doc.create_experimental_level(exp_condition, [exp_vars[j]], repr(exp_var_data[j]), input_id)

    output_data = table_data['output']
    for i in range(0, len(output_data)):
        doc.create_outcome_level(exp_conditions[i], out_vars, repr(output_data[i]), 'output')

    return exp_conditions
    
def load_experiment(plan_data, doc):
    exp_id = load_alnum_id(plan_data['id'])

    return doc.create_experiment(exp_id, plan_data['name'])

def load_design_doc():
    doc = XDocument()

    doc.displayId = SD2_DESIGN_ID
    doc.name = SD2_DESIGN_NAME
    doc.version = '1'

    return doc

def load_experiment_doc():
    doc = XDocument()

    doc.displayId = SD2_EXP_ID
    doc.name = SD2_EXP_NAME
    doc.description = "This collection contains all experiments carried out as part of the DARPA SD2 (Synergistic Discovery and Design) program, as well as sub-collections for each challenge problem in the program."
    doc.version = '1'

    return doc

def load_plan_doc(plan_data):
    exp_id = load_alnum_id(plan_data['id'])

    doc = XDocument()

    doc.displayId = exp_id
    doc.name = plan_data['name']
    try:
        doc.description = plan_data['description']
    except:
        doc.description = "This collection contains metadata for an experiment carried out as part of an SD2 challenge problem."
    doc.version = '1'

    return doc

def convert_xplan_to_sbol(plan_data, plan_path, exp_path, om_path, validate, namespace=None):
    exp_doc = load_experiment_doc()
    exp_doc.configure_namespace(SD2_EXP_NS)
    exp_doc.configure_options(validate, False)

    exp = load_experiment(plan_data, exp_doc)

    plan_doc = load_plan_doc(plan_data)
    if namespace is None:
        plan_doc.configure_namespace(''.join([SD2_NS, '/', exp.displayId]))
    else:
        plan_doc.configure_namespace(namespace)

    try:
        exp_vars = []
        out_vars = []

        exp_intent = load_experimental_intent(plan_data, plan_doc, exp, exp_vars, out_vars)

        load_truth_table(plan_data, plan_doc, exp_intent, exp_vars, out_vars)
    except:
        pass

    exp_data_dict = {}

    om = plan_doc.read_om(om_path)

    for step_data in plan_data['steps']:
        load_step_entities(step_data, plan_doc, exp, exp_data_dict, om)
    
    act_dict = {}

    for step_data in plan_data['steps']:
        load_step_activities(step_data, plan_doc, exp_data_dict, act_dict, om)

    return (plan_doc, exp_doc)

"""
Does the attachment already exist? e.g. for re-upload
"""
def read_attachment(uri, json_file_name):

    sparql = SPARQLWrapper("https://hub-api.sd2e.org/sparql")
    query = """
    select ?attachment_name where
    {{
      <{}> <http://wiki.synbiohub.org/wiki/Terms/synbiohub#attachment> ?attachment_id .
      ?attachment_id <http://purl.org/dc/terms/title> ?attachment_name .
    }}
    """.format(uri)

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    
    if len(results['results']['bindings']) != 0:
        for attachment_value in results['results']['bindings']:
            found_attachment_name = attachment_value['attachment_name']['value']
            if json_file_name == found_attachment_name:
                print("Already found attachment, {} skipping".format(json_file_name))
                return True
    return False

def create_intent_file_name(plan_path):
    return os.path.splitext(plan_path)[0] + '_intent.json'

def create_sample_attributes_file_name(plan_path):
    return os.path.splitext(plan_path)[0] + '_sample_attributes.json'

"""
Generic method for JSON upload
"""
def post_upload_json(uri, json_data, json_file_name, url, email, password, delete=False):

    found_attachment = read_attachment(uri, json_file_name)
    if found_attachment:
        return True

    sbh = SynBioHub(url,
                    email,
                    password,
                    'http://hub-api.sd2e.org:80/sparql',
                    {'http://sd2e.org#bead_model', 'http://sd2e.org#bead_batch'})

    if not os.path.exists(json_file_name):
        with open(json_file_name, "w") as outfile:
            json.dump(json_data, outfile)

    sbh.attach_file(json_file_name, uri)

    if delete:
        os.remove(json_file_name)
    return True

"""
Link some control information, if known: beads, wild-type to the plan URI
This supports plan-automated FCS processing
"""
def post_upload_controls(plan_data):

    plan_id = plan_data['id']
    sparql = SPARQLWrapper("https://hub-api.sd2e.org/sparql")

    bead_uris = []
    save_wt_uri = None

    # look up bead samples for plan
    query = """
    select distinct ?sample where
    {{
      <{}> <http://sd2e.org#experimentalData> ?data .
      ?data <http://www.w3.org/ns/prov#wasDerivedFrom>+ <https://hub.sd2e.org/user/sd2e/design/beads_spherotech_rainbow/1> .
      ?data <http://www.w3.org/ns/prov#wasDerivedFrom> ?sample .
    }}
    """.format(plan_id)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()['results']['bindings']
    for result in results:
      bead_uri = result['sample']['value']
      bead_uris.append(bead_uri)

    # look up WT for plan
    # NCIT_C62195 is the ontology term for a wild type design
    query = """
    select distinct ?sample where
    {{
      <{}> <http://sd2e.org#experimentalData> ?data .
      ?sample <http://sbols.org/v2#role> <http://purl.obolibrary.org/obo/NCIT_C62195> .
      ?data <http://www.w3.org/ns/prov#wasDerivedFrom>+ ?sample .
    }}
    """.format(plan_id)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()['results']['bindings']
    for result in results:
      wt_uri = result['sample']['value']
      if save_wt_uri == None:
        save_wt_uri = wt_uri

    bead_write_results = {}
    bead_write_results['results'] = { 'bindings' : [] }
    for bead_uri in bead_uris:
      print("Writing bead control: " + plan_id + " " + bead_uri)

      query = """
      WITH <https://hub.sd2e.org/user/sd2e> 
      INSERT {{
      <{}> <http://sd2e.org#bead_control> <{}> .
      }}""".format(plan_id, bead_uri)
      sparql.setQuery(query)
      sparql.setReturnFormat(JSON)
      bead_write_results['results']['bindings'].extend(sparql.query().convert()['results']['bindings'])

    if save_wt_uri != None:
      print("Writing wild type as negative control: " + plan_id + " " + save_wt_uri)

      query = """
      WITH <https://hub.sd2e.org/user/sd2e>
      INSERT {{
      <{}> <http://sd2e.org#negative_control> <{}> .
      }} 
      """.format(plan_id, save_wt_uri)
      sparql.setQuery(query)
      sparql.setReturnFormat(JSON)
      bead_write_results['results']['bindings'].extend(sparql.query().convert()['results']['bindings'])
      return bead_write_results

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input')
    parser.add_argument('-o1', '--plan', nargs='?', default='example/sbol/plan.xml')
    parser.add_argument('-o2', '--experiment', nargs='?', default='example/sbol/experiment.xml')
    # parser.add_argument('-o3', '--design', nargs='?', default=None)
    parser.add_argument('-m', '--om', nargs='?', default='example/om/om-2.0.rdf')
    parser.add_argument('-v', '--validate', action='store_true')
    parser.add_argument('-w', '--overwrite', action='store_true')
    parser.add_argument('-n', '--namespace', nargs='?', default=None)
    parser.add_argument('-u', '--url', nargs='?', default='https://hub.sd2e.org/')
    parser.add_argument('-e', '--email', nargs='?', default='sd2_service@sd2e.org')
    parser.add_argument('-p', '--password', nargs='?', default=None)
    
    args = parser.parse_args(args)

    with open(args.input) as plan_file:
        plan_data = json.load(plan_file)

        docs = convert_xplan_to_sbol(plan_data, args.plan, args.experiment, args.om, args.validate, args.namespace)

        if args.password is None:
            docs[0].write(args.plan)
            docs[1].write(args.experiment)

        if args.password is not None:
            result = docs[0].upload(args.url, args.email, args.password)
            if result == 'Submission id and version already in use':
                if args.overwrite:
                    docs[0].upload(args.url, args.email, args.password, ''.join([SD2S_NS, '/', docs[0].displayId, '/', docs[0].displayId + '_collection/1']), 1)
                    docs[1].upload(args.url, args.email, args.password, SD2_EXP_COLLECTION, 2)
                    print('Plan overwritten.')
                else:
                    print('Plan ID is already used and would be overwritten. Upload aborted. To overwrite, include -w in arguments.')
            else:
                docs[1].upload(args.url, args.email, args.password, SD2_EXP_COLLECTION, 2)
                print('Plan uploaded.')

            #upload intent
            plan_base_name = os.path.basename(args.input)
            plan_id = plan_data["id"]

            if "intent" in plan_data and plan_data["intent"] is not None:
                post_upload_json(plan_id, plan_data["intent"], create_intent_file_name(plan_base_name), args.url, args.email, args.password)
            
            post_upload_controls(plan_data)

            # upload plan
            post_upload_json(plan_id, plan_data, plan_base_name, args.url, args.email, args.password)

            #upload sample attributes
            sample_attribute_path = create_sample_attributes_file_name(plan_base_name)
            with open(sample_attribute_path) as plan_sample_attributes_file:
                plan_sample_attributes_data = json.load(plan_sample_attributes_file)
                post_upload_json(plan_id, plan_sample_attributes_data, plan_sample_attributes_file, args.url, args.email, args.password)

    print('done')

if __name__ == '__main__':
    main()