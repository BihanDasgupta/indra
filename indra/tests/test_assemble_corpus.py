import pickle
from copy import deepcopy
from indra.statements import *
from indra.tools import assemble_corpus as ac


a = Agent('a', db_refs={'HGNC': '1234', 'TEXT': 'a'})
b = Agent('b', db_refs={'UP': 'P15056', 'TEXT': 'b'})
c = Agent('c', db_refs={'FPLX': 'XXX', 'TEXT': 'c'})
d = Agent('d', db_refs={'TEXT': 'd'})
e = Agent('e', db_refs={'CHEBI': 'CHEBI:1234', 'TEXT': 'e'})
f = Agent('b', db_refs={'UP': 'P28028', 'TEXT': 'b'})
g = Agent('g', db_refs={'FPLX': 'ERK'})
h = Agent('g', mods=['x', 'y'], mutations=['x', 'y'], activity='x',
               location='nucleus', bound_conditions=['x', 'y', 'z'])
i = Agent('a', db_refs={'HGNC': '1234', 'TEXT': 'a'},
          bound_conditions=[BoundCondition(d)])
j = Agent('a', db_refs={'HGNC': '1234', 'TEXT': 'a'},
          bound_conditions=[BoundCondition(b)])
k = Agent('a', db_refs={'HGNC': '1234', 'TEXT': 'a'},
          bound_conditions=[BoundCondition(f)])
l = Agent('a', db_refs={'HGNC': '1234', 'TEXT': 'a'},
          bound_conditions=[BoundCondition(a)])

mapk1 = Agent('MAPK1', db_refs={'HGNC':'6871', 'UP':'P28482'})
erk = Agent('ERK', db_refs={'FPLX': 'ERK'})
st1 = Phosphorylation(a, b, evidence=[Evidence(text='a->b', source_api='assertion')])
st2 = Phosphorylation(a, d, evidence=[Evidence(text='a->d', source_api='assertion')])
st3 = Phosphorylation(c, d, evidence=[Evidence(text='c->d', source_api='assertion')])
st4 = Phosphorylation(b, e, evidence=[Evidence(text='b->e', source_api='assertion')])
st5 = Phosphorylation(None, b, evidence=[Evidence(text='->b', source_api='assertion')])
st6 = Phosphorylation(None, d, evidence=[Evidence(text='->d', source_api='assertion')])
st7 = Phosphorylation(None, e, evidence=[Evidence(text='->e', source_api='assertion')])
st8 = Phosphorylation(b, f, evidence=[Evidence(text='b->f', source_api='assertion')])
st9 = Phosphorylation(None, f, evidence=[Evidence(text='->f', source_api='assertion')])
st10 = Phosphorylation(None, g, evidence=[Evidence(text='->g', source_api='assertion')])
st11 = Phosphorylation(None, h, evidence=[Evidence(text='->h', source_api='assertion')])
st12 = Phosphorylation(a, b, evidence=[Evidence(epistemics={'direct': True})])
st13 = Phosphorylation(a, b, evidence=[Evidence(epistemics={'direct': False})])
st14 = Activation(a, b, 'activity')
st15 = Activation(a, b, 'kinase')
st14.supports = [st15]
st15.supported_by = [st14]
st16 = Phosphorylation(a, mapk1)
st17 = Phosphorylation(a, erk)
st18 = Phosphorylation(a, i)
st19 = Phosphorylation(a, j)
st20 = Phosphorylation(a, k)
st21 = Phosphorylation(a, l)
st1.belief = 0.9
st2.belief = 0.8
st3.belief = 0.7


def test_load_stmts():
    with open('_test.pkl', 'wb') as fh:
        pickle.dump([st1], fh)
    st_loaded = ac.load_statements('_test.pkl')
    assert len(st_loaded) == 1
    assert st_loaded[0].equals(st1)


def test_dump_stmts():
    ac.dump_statements([st1], '_test.pkl')
    st_loaded = ac.load_statements('_test.pkl')
    assert len(st_loaded) == 1
    assert st_loaded[0].equals(st1)


def test_filter_grounded_only():
    # st18 has and i, which has an ungrounded bound condition
    st_out = ac.filter_grounded_only([st1, st4])
    assert len(st_out) == 2
    st_out = ac.filter_grounded_only([st3])
    assert len(st_out) == 0

    # Do we filter out a statement with an ungrounded bound condition?
    st_out = ac.filter_grounded_only([st18])
    assert len(st_out) == 0

    # When we request to remove ungrounded bound conditions, do we?
    st18_copy = deepcopy(st18)
    assert len(st18_copy.sub.bound_conditions) == 1
    st_out = ac.filter_grounded_only([st18_copy], remove_bound=True)
    assert len(st_out[0].sub.bound_conditions) == 0

    # When we request to remove ungrounded bound conditions, do we leave
    # grounded bound conditions in place?
    st19_copy = deepcopy(st19)
    assert len(st19_copy.sub.bound_conditions) == 1
    st_out = ac.filter_grounded_only([st19_copy], remove_bound=True)
    assert len(st_out[0].sub.bound_conditions) == 1

    # Do we filter out a statement with an grounded bound condition?
    st_out = ac.filter_grounded_only([st19])
    assert len(st_out) == 1


def test_filter_grounded_only_score():
    c1 = Event(Concept('x', db_refs={'a': [('x', 0.5), ('y', 0.8)]}))
    c2 = Event(Concept('x', db_refs={'a': [('x', 0.7), ('y', 0.9)]}))
    st1 = Influence(c1, c2)
    assert len(ac.filter_grounded_only([st1])) == 1
    assert len(ac.filter_grounded_only([st1], score_threshold=0.4)) == 1
    assert len(ac.filter_grounded_only([st1], score_threshold=0.6)) == 1
    assert len(ac.filter_grounded_only([st1], score_threshold=0.85)) == 0
    assert len(ac.filter_grounded_only([st1], score_threshold=0.95)) == 0
    c3 = Event(Concept('x', db_refs={'a': []}))
    st2 = Influence(c1, c3)
    assert len(ac.filter_grounded_only([st2])) == 0


def test_filter_uuid_list():
    st_out = ac.filter_uuid_list([st1, st4], [st1.uuid])
    assert len(st_out) == 1


def test_filter_genes_only():
    st_out = ac.filter_genes_only([st1, st5])
    assert len(st_out) == 2
    st_out = ac.filter_genes_only([st6, st7])
    assert len(st_out) == 0
    st_out = ac.filter_genes_only([st4])
    assert len(st_out) == 0
    st_out = ac.filter_genes_only([st3], specific_only=True)
    assert len(st_out) == 0

    # Can we remove statements with non-gene bound conditions?
    st_out = ac.filter_genes_only([st18])  # remove_bound defaults to False
    assert len(st_out) == 0
    st_out = ac.filter_genes_only([st18], remove_bound=False)
    assert len(st_out) == 0

    # Can we remove non-gene bound conditions?
    st18_copy = deepcopy(st18)
    assert len(st18_copy.sub.bound_conditions) == 1
    st_out = ac.filter_genes_only([st18_copy], remove_bound=True)
    assert len(st_out[0].sub.bound_conditions) == 0


def test_filter_human_only():
    st_out = ac.filter_human_only([st1, st5])
    assert len(st_out) == 2
    st_out = ac.filter_human_only([st8, st9])
    assert len(st_out) == 0

    # Can we filter out statements with bound conditions grounded to non-human
    # genes?
    st_out = ac.filter_human_only([st20], remove_bound=False)
    assert len(st_out) == 0

    # When we do such filtering, do we keep statements bounded to human genes?
    st_out = ac.filter_human_only([st21], remove_bound=False)
    assert len(st_out) == 1

    # Can we remove bound conditions grounded to non-human genes?
    st_out = ac.filter_human_only([st20], remove_bound=True)
    assert len(st_out) == 1
    assert len(st_out[0].sub.bound_conditions) == 0

    # When we do so, do we keep bound conditions not grounded to non-human
    # genes?
    st_out = ac.filter_human_only([st21], remove_bound=True)
    assert len(st_out) == 1
    assert len(st_out[0].sub.bound_conditions) == 1


def test_filter_gene_list_one():
    st_out = ac.filter_gene_list([st1, st2], ['a'], 'one')
    assert len(st_out) == 2
    st_out = ac.filter_gene_list([st1, st2], ['a'], 'all')
    assert len(st_out) == 0
    st_out = ac.filter_gene_list([st1, st2], ['a', 'b'], 'all')
    assert len(st_out) == 1
    st_out = ac.filter_gene_list([st1, st2], ['a', 'b'], 'invalid')
    assert len(st_out) == 2

    # Can we exclude a statement with a bound condition agent not on the filter
    # list?
    st_out = ac.filter_gene_list([st18], ['a', 'b', 'd'], 'all')
    # All genes in the list
    assert len(st_out) == 1
    st_out = ac.filter_gene_list([st18], ['a', 'b'], 'all')
    # Bound condition for sub not in list
    assert len(st_out) == 0
    st_out = ac.filter_gene_list([st18], ['a', 'b'], 'one')
    # Bound condition for sub not in list but we only need to match one
    assert len(st_out) == 1
    st_out = ac.filter_gene_list([st18], ['d'], 'one')
    # Only the bound condition is in filter list
    assert len(st_out) == 1

    # Can we remove bound conditions that are not in the filter list?
    st_out = ac.filter_gene_list([st18], ['a', 'b', 'd'], 'all',
                                 remove_bound=True)
    assert len(st_out[0].sub.bound_conditions) == 1
    st_out = ac.filter_gene_list([st18], ['a', 'b'], 'all',
                                 remove_bound=True)
    assert len(st_out[0].sub.bound_conditions) == 0


def test_filter_gene_list_invert():
    st_out = ac.filter_gene_list([st1, st2], ['a'], 'one', invert=True)
    assert len(st_out) == 0
    st_out = ac.filter_gene_list([st1, st2], ['d'], 'one', invert=True)
    assert len(st_out) == 1
    assert st_out[0].sub.name == 'b'
    st_out = ac.filter_gene_list([st1, st2], ['a', 'd'], 'all', invert=True)
    assert len(st_out) == 1
    assert st_out[0].sub.name == 'b'
    st_out = ac.filter_gene_list([st1, st2], ['a', 'b', 'd'], 'all',
                                 invert=True)
    assert len(st_out) == 0


def test_filter_gene_list_families():
    stmts_out = ac.filter_gene_list([st16, st17], ['MAPK1'], 'one',
                                    allow_families=False)
    assert len(stmts_out) == 1
    assert stmts_out[0] == st16
    stmts_out = ac.filter_gene_list([st16, st17], ['MAPK1'], 'one',
                                    allow_families=True)
    assert len(stmts_out) == 2
    assert st16 in stmts_out
    assert st17 in stmts_out


def test_run_preassembly():
    st_out = ac.run_preassembly([st1, st3, st5, st6])
    assert len(st_out) == 2


def test_run_preassembly_all_stmts():
    st_out = ac.run_preassembly([st1, st3, st5, st6], return_toplevel=False)
    assert len(st_out) == 4


def test_expand_families():
    st_out = ac.expand_families([st10])
    assert len(st_out) == 2


def test_strip_agent_context():
    st_out = ac.strip_agent_context([st11])
    assert len(st_out) == 1
    assert not st_out[0].sub.mods
    assert not st_out[0].sub.mutations
    assert not st_out[0].sub.bound_conditions
    assert not st_out[0].sub.activity
    assert not st_out[0].sub.location


def test_filter_direct():
    st_out = ac.filter_direct([st12])
    assert len(st_out) == 1
    st_out = ac.filter_direct([st13])
    assert len(st_out) == 0


def test_filter_belief():
    st_out = ac.filter_belief([st1, st2, st3], 0.75)
    assert len(st_out) == 2


def test_reduce_activities():
    st_out = ac.reduce_activities([st14, st15])
    assert st_out[0].obj_activity == 'kinase'
    assert st_out[1].obj_activity == 'kinase'


def test_filter_source():
    ev1 = Evidence(source_api='bel')
    ev2 = Evidence(source_api='biopax')
    ev3 = Evidence(source_api='reach')
    st1 = Activation(Agent('a'), Agent('b'), evidence=[ev3])
    st2  = Activation(Agent('a'), Agent('b'), evidence=[ev1, ev2])
    st3 = Activation(Agent('a'), Agent('b'), evidence=[ev1, ev3])
    st_out = ac.filter_evidence_source([st1, st2], ['reach'], 'one')
    assert len(st_out) == 1
    st_out = ac.filter_evidence_source([st1, st2, st3], ['reach'], 'all')
    assert (len(st_out) == 2)
    st_out = ac.filter_evidence_source([st1, st2, st3], ['bel', 'biopax'],
                                       'one')
    assert (len(st_out) == 2)
    st_out = ac.filter_evidence_source([st1, st2, st3], ['bel', 'biopax'],
                                       'all')
    assert (len(st_out) == 1)
    st_out = ac.filter_evidence_source([st1, st2, st3], ['bel', 'biopax'],
                                       'none')
    assert (len(st_out) == 1)


def test_map_grounding():
    a = Agent('MEK', db_refs={'TEXT': 'MEK'})
    b = Agent('X', db_refs={'TEXT': 'ERK'})
    st = Activation(a, b)
    st_out = ac.map_grounding([st], do_rename=False)
    assert len(st_out) == 1
    assert st_out[0].subj.db_refs.get('FPLX')
    assert st_out[0].obj.db_refs.get('FPLX')
    assert st_out[0].obj.name == 'X'
    st_out = ac.map_grounding([st], do_rename=True)
    assert len(st_out) == 1
    assert st_out[0].subj.db_refs.get('FPLX')
    assert st_out[0].obj.db_refs.get('FPLX')
    assert st_out[0].obj.name == 'ERK'


def test_map_grounding_user_map():
    gm = {'MEK': {'XXX': 'YYY'}, 'ERK': {'FPLX': 'ERK'}}
    a = Agent('MEK', db_refs={'TEXT': 'MEK'})
    b = Agent('X', db_refs={'TEXT': 'ERK'})
    st = Activation(a, b)
    st_out = ac.map_grounding([st], grounding_map=gm, do_rename=True)
    assert len(st_out) == 1
    assert st_out[0].subj.db_refs.get('XXX') == 'YYY'
    assert st_out[0].obj.db_refs.get('FPLX') == 'ERK'
    assert st_out[0].obj.name == 'ERK'
    gm = {'ERK': {'FPLX': 'ERK_TEST'}}
    st_out = ac.map_grounding([st], grounding_map=gm,
                              grounding_map_policy='extend')
    assert len(st_out) == 1
    assert st_out[0].subj.db_refs.get('FPLX') == 'MEK'
    assert st_out[0].obj.db_refs.get('FPLX') == 'ERK_TEST'
    st_out = ac.map_grounding([st])
    # Make sure the extension to the default grounding map doesn't persist
    assert len(st_out) == 1
    assert st_out[0].subj.db_refs.get('FPLX') == 'MEK'
    assert st_out[0].obj.db_refs.get('FPLX') == 'ERK'
    assert st_out[0].obj.name == 'ERK'


def test_map_sequence():
    a = Agent('MAPK1', db_refs={'UP': 'P28482', 'HGNC': '6871'})
    st1 = Phosphorylation(None, a, 'T', '182')
    st2 = Phosphorylation(None, a, 'T', '185')
    st3 = Phosphorylation(None, a, 'Y', '999')
    st_out = ac.map_sequence([st1])
    assert len(st_out) == 1, st_out
    assert st_out[0].position == '185'
    st_out = ac.map_sequence([st2])
    assert len(st_out) == 1, st_out
    assert st_out[0].position == '185'
    st_out = ac.map_sequence([st3])
    assert len(st_out) == 0, st_out


def test_map_sequence_blank_entries():
    """Make sure sites curated as erroneous with no mappings don't
    get treated as valid mappings."""
    mapk1 = Agent('MAPK1', db_refs={'UP': 'P28482'})
    rps6 = Agent('RPS6', db_refs={'UP': 'P62753'})
    phos_rps6 = Agent('RPS6',
                 mods=[ModCondition('phosphorylation', 'T', '389')],
                 db_refs={'UP': 'P62753'})
    st1 = Phosphorylation(mapk1, rps6, 'T', '389')
    st2 = Phosphorylation(phos_rps6, mapk1, 'T', '185')
    mapped = ac.map_sequence([st1, st2])
    assert len(mapped) == 0


def test_filter_by_type():
    st_out = ac.filter_by_type([st1, st14], Phosphorylation)
    assert len(st_out) == 1
    st_out = ac.filter_by_type([st1, st14], "Phosphorylation")
    assert len(st_out) == 1


def test_filter_top_level():
    st_out = ac.filter_top_level([st14, st15])
    assert len(st_out) == 1


def test_filter_no_hypothesis():
    a = Agent('MAPK1')
    ev1 = Evidence(epistemics={'hypothesis': True})
    ev2 = Evidence(epistemics={'hypothesis': False})
    st1 = Phosphorylation(None, a, evidence=[ev1, ev2])
    st2 = Phosphorylation(None, a, evidence=[ev1, ev1])
    st_out = ac.filter_no_hypothesis([st1, st2])
    assert len(st_out) == 1


def test_filter_no_negated():
    a = Agent('MAPK1')
    ev1 = Evidence(epistemics={'negated': True})
    ev2 = Evidence(epistemics={'negated': False})
    st1 = Phosphorylation(None, a, evidence=[ev1, ev2])
    st2 = Phosphorylation(None, a, evidence=[ev1, ev1])
    st_out = ac.filter_no_negated([st1, st2])
    assert len(st_out) == 1


def test_belief_cut_plus_filter_top():
    st1 = Phosphorylation(None, Agent('a'))
    st2 = Phosphorylation(Agent('b'), Agent('a'))
    st1.supports = [st2]
    st2.supported_by = [st1]
    st1.belief = 0.9
    st2.belief = 0.1
    st_high_belief = ac.filter_belief([st1, st2], 0.5)
    st_top_level = ac.filter_top_level(st_high_belief)
    assert len(st_top_level) == 1


def test_filter_inconsequential_mods():
    mc = ModCondition('phosphorylation', None, None, True)
    st1 = Phosphorylation(None, Agent('a'))
    st2 = Phosphorylation(Agent('a', mods=[mc]), Agent('b'))
    st_out = ac.filter_inconsequential_mods([st1, st2])
    assert len(st_out) == 1
    whitelist = {'b': [('phosphorylation', None, None)]}
    st_out = ac.filter_inconsequential_mods([st1, st2], whitelist=whitelist)
    assert len(st_out) == 2


def test_filter_inconsequential_mods2():
    st1 = Phosphorylation(Agent('a'), Agent('b'), 'S', '315')
    whitelist = {'b': [('phosphorylation', 'S', '315')]}
    st_out = ac.filter_inconsequential_mods([st1, st2], whitelist=whitelist)
    assert len(st_out) == 1


def test_filter_inconsequential_activities():
    st1 = Activation(Agent('a', activity=ActivityCondition('kinase', True)),
                     Agent('b'), 'activity')
    st2 = Activation(Agent('c'), Agent('a'), 'kinase')
    st_out = ac.filter_inconsequential_acts([st1, st2])
    assert len(st_out) == 1
    st_out = ac.filter_inconsequential_acts(st_out)
    assert len(st_out) == 0


def test_filter_mutation_status():
    braf_mut = Agent('BRAF', mutations=MutCondition('600', 'V', 'E'))
    braf_other_mut = Agent('BRAF', mutations=MutCondition('555', 'K', 'G'))
    st1 = Phosphorylation(braf_mut, Agent('a'))
    st2 = Phosphorylation(braf_other_mut, Agent('a'))
    mutations = {'BRAF': [('V', '600', 'E')]}
    deletions = []
    st_out = ac.filter_mutation_status([st1, st2], mutations, deletions)
    assert len(st_out) == 1
    mutations = {}
    deletions = ['a']
    st_out = ac.filter_mutation_status([st1, st2], mutations, deletions)
    assert len(st_out) == 0

    # Can we filter statements out based on bound conditions?
    mutations = {'BRAF': [('V', '600', 'E')]}
    deletions = []
    braf_good_bound = deepcopy(braf_mut)
    braf_good_bound.bound_conditions = [BoundCondition(braf_mut)]
    #
    braf_bad_bound = deepcopy(braf_mut)
    braf_bad_bound.bound_conditions = [BoundCondition(braf_other_mut)]
    #
    st3 = Phosphorylation(braf_good_bound, Agent('a'))
    st4 = Phosphorylation(braf_bad_bound, Agent('a'))
    #
    st_out = ac.filter_mutation_status([st3], mutations, deletions)
    assert len(st_out) == 1
    #
    st_out = ac.filter_mutation_status([st4], mutations, deletions)
    assert len(st_out) == 0

    # Can we remove bound conditions based on our filter?
    st_out = ac.filter_mutation_status([st3], mutations, deletions,
                                       remove_bound=True)
    assert len(st_out[0].enz.bound_conditions) == 1
    #
    st_out = ac.filter_mutation_status([st4], mutations, deletions,
                                       remove_bound=True)
    assert len(st_out[0].enz.bound_conditions) == 0


def test_get_unreachable_mods():
    st1 = Phosphorylation(Agent('X'), Agent('Y'), 'S', '222')
    mcs = [ModCondition('phosphorylation', 'S', '218', True),
           ModCondition('phosphorylation', 'S', '222', True)]
    st2 = ActiveForm(Agent('Y', mods=mcs), 'activity', True)
    res = ac.get_unreachable_mods([st1, st2])
    assert 'Y' in res, res
    assert res['Y'] == set([('phosphorylation', 'S', '218')])


def test_rename_db_ref():
    x = Agent('X', db_refs={'BE': 'X'})
    y = Agent('Y', db_refs={'FPLX': 'Y'})
    st1 = Phosphorylation(x, y)
    stmts = ac.rename_db_ref([st1], 'BE', 'FPLX')
    assert len(stmts) == 1
    assert stmts[0].enz.db_refs.get('FPLX') == 'X'
    assert 'BE' not in stmts[0].enz.db_refs
    assert stmts[0].sub.db_refs.get('FPLX') == 'Y'


def test_filter_concept_names():
    stmts = [
        Influence(Event(Concept('a')), Event(Concept('b'))),
        Influence(Event(Concept('a')), Event(Concept('c'))),
        Influence(Event(Concept('a')), Event(Concept('d'))),
        Influence(Event(Concept('c')), Event(Concept('d')))
        ]

    stmts_out = ac.filter_concept_names(stmts, ['a'], 'one')
    assert len(stmts_out) == 3, stmts_out
    stmts_out = ac.filter_concept_names(stmts, ['a', 'b', 'c'], 'all')
    assert len(stmts_out) == 2, stmts_out
    stmts_out = ac.filter_concept_names(stmts, ['a', 'd'], 'one')
    assert len(stmts_out) == 4, stmts_out
    stmts_out = ac.filter_concept_names(stmts, ['a', 'b'], 'one', invert=True)
    assert len(stmts_out) == 1, stmts_out


def test_filter_namespace_concepts_simple():
    def make_statement(a, b):
        return Influence(Event(Concept(a, db_refs={'TEXT': a})),
                         Event(Concept(b, db_refs={'TEXT': b})))
    stmts = [make_statement('education', 'thinking'),
             make_statement('doubt', 'government')]
    fs = ac.filter_by_db_refs(stmts, 'TEXT', ['education'], 'one')
    assert [stmts[0]] == fs, fs
    fs = ac.filter_by_db_refs(stmts, 'TEXT', ['education'], 'one',
                                        invert=True)
    assert stmts == fs, fs
    fs = ac.filter_by_db_refs(stmts, 'TEXT', ['education'], 'all',
                                        invert=True)
    assert [stmts[1]] == fs, fs
    fs = ac.filter_by_db_refs(stmts, 'TEXT', ['education'], 'all')
    assert not fs, fs


def test_filter_namespace_concepts_list():
    def make_statement(a, b):
        return Influence(Event(Concept(a, db_refs={'UN': [(a, 1.0)]})),
                         Event(Concept(b, db_refs={'UN': [(b, 1.0)]})))
    stmts = [make_statement('UN/entities/human/education',
                'UN/entities/human/food/food_security'),
             make_statement('UN/entities/human/fishery',
                'UN/entities/human/government')]
    fs = ac.filter_by_db_refs(stmts, 'UN', ['education'], 'one',
                                        match_suffix=True)
    assert [stmts[0]] == fs, fs
    fs = ac.filter_by_db_refs(stmts, 'UN', ['education', 'fishery'],
                                        'one', match_suffix=True)
    assert stmts == fs, fs
    fs = ac.filter_by_db_refs(stmts, 'UN',
                                        ['fishery', 'government'], 'all',
                                        match_suffix=True)
    assert [stmts[1]] == fs, fs


def test_merge_groundings():
    refs1 = {'UN': [('x', 0.8), ('y', 0.7)],
             'B': 'x',
             'C': 'y'}
    refs2 = {'UN': [('x', 0.9), ('y', 0.6), ('z', 0.5)],
             'B': 'x',
             'D': 'z'}
    stmts = [Influence(Event(Concept('a', db_refs=refs1)),
                       Event(Concept('b', db_refs=refs2)),
                       evidence=[Evidence(source_api='eidos', text='1')]),
             Influence(Event(Concept('a', db_refs=refs2)),
                       Event(Concept('b', db_refs=refs1)),
                       evidence=[Evidence(source_api='eidos', text='2')])]
    stmts = ac.run_preassembly(stmts)
    assert len(stmts) == 1
    stmts = ac.merge_groundings(stmts)
    assert stmts[0].subj.concept.db_refs == \
           {'UN': [('x', 0.9), ('y', 0.7), ('z', 0.5)],
            'B': 'x', 'C': 'y', 'D': 'z'}, \
        stmts[0].subj.db_refs
    assert stmts[0].obj.concept.db_refs == stmts[0].subj.concept.db_refs


def test_preassemble_flatten():
    st_out = ac.run_preassembly([st1, st3, st5, st6], flatten_evidence=False)
    assert len(st_out[0].evidence) == 1
    assert len(st_out[1].evidence) == 1
    st_out = ac.run_preassembly([st1, st3, st5, st6], flatten_evidence=True,
                                flatten_evidence_collect_from='supported_by')
    assert len(st_out[0].evidence) == 2
    assert len(st_out[1].evidence) == 2
    st_out = ac.run_preassembly([st1, st3, st5, st6], flatten_evidence=True,
                                flatten_evidence_collect_from='supports')
    assert len(st_out[0].evidence) == 1
    assert len(st_out[1].evidence) == 1


def test_filter_by_curation():
    new_st1 = deepcopy(st1)
    new_ev = Evidence(text='a -> b', source_api='new')
    new_st1.evidence.append(new_ev)
    stmts_in = [new_st1, st2, st3]
    assert len(new_st1.evidence) == 2
    assert all(st.belief != 1 for st in stmts_in)

    cur1 = {'pa_hash': new_st1.get_hash(),
            'source_hash': new_st1.evidence[0].get_source_hash(),
            'tag': 'grounding'}
    cur2 = {'pa_hash': new_st1.get_hash(),
            'source_hash': new_st1.evidence[1].get_source_hash(),
            'tag': 'wrong_relation'}
    cur3 = {'pa_hash': new_st1.get_hash(),
            'source_hash': new_st1.evidence[0].get_source_hash(),
            'tag': 'correct'}
    cur4 = {'pa_hash': st2.get_hash(),
            'source_hash': st2.evidence[0].get_source_hash(),
            'tag': 'correct'}
    # With 'any' policy it is enough to have one incorrect curation
    any_incorrect_one_cur = ac.filter_by_curation(stmts_in, [cur1], 'any')
    assert len(any_incorrect_one_cur) == 2
    assert new_st1 not in any_incorrect_one_cur
    # With 'all' policy all evidences have to be curated
    all_incorrect_one_cur = ac.filter_by_curation(stmts_in, [cur1], 'all')
    assert len(all_incorrect_one_cur) == 3, len(all_incorrect_one_cur)
    assert new_st1 in all_incorrect_one_cur
    all_incorrect_two_cur = ac.filter_by_curation(stmts_in, [cur1, cur2], 'all')
    assert len(all_incorrect_two_cur) == 2
    assert new_st1 not in all_incorrect_two_cur
    # Correct curation cancels out incorrect
    assert len(new_st1.evidence) == 2
    correct_incorrect = ac.filter_by_curation(
        stmts_in, [cur1, cur2, cur3, cur4], 'all', update_belief=False)
    assert len(correct_incorrect) == 3, len(correct_incorrect)
    assert new_st1 in correct_incorrect
    # new_st1.evidence[1] should be filtered out because there's only incorrect
    # curation(cur2), new_st1.evidence[0] stays because correct cancels out
    # incorrect (cur1, cur3)
    assert len(new_st1.evidence) == 1
    assert new_st1.evidence[0].source_api == 'assertion'
    assert all(st.belief != 1 for st in correct_incorrect)
    # Optionally update belief to 1 for correct curation
    new_belief = ac.filter_by_curation(
        stmts_in, [cur1, cur2, cur3, cur4], 'all', update_belief=True)
    assert new_belief[0].belief == 1
    assert new_belief[1].belief == 1
    assert new_belief[2].belief == 0.7
    # Make sure that if all evidence are incorrect, statement is filtered out
    # (even if the overall statement is correct according to external
    # evidence curation)
    external_ev = Evidence(text='a activates b', source_api='external')
    external_cur = {'pa_hash': new_st1.get_hash(),
                    'source_hash': external_ev.get_source_hash(),
                    'tag': 'correct'}
    correct_external = ac.filter_by_curation(
        [new_st1], [cur1, cur2, external_cur], 'any')
    assert len(correct_external) == 0
    # If we add the external correct evidence, statement is not filtered out
    new_st1.evidence.append(external_ev)
    updated = ac.filter_by_curation(
        [new_st1], [cur1, cur2, external_cur], 'any')
    assert len(updated) == 1
    assert new_st1 in updated
    assert len(new_st1.evidence) == 1


def test_eidos_ungrounded():
    a = Agent('x', db_refs={'TEXT': 'x', 'TEXT_NORM': 'y'})
    b = Agent('x', db_refs={'TEXT': 'x', })
    c = Agent('x', db_refs={'TEXT': 'x', 'GO': 'GO:1234'})
    stmts = [Activation(a, b),
             Activation(a, c),
             Activation(b, c),
             Activation(c,c)]
    stmts_out = ac.filter_grounded_only(stmts)
    assert len(stmts_out) == 1


def test_filter_large_complexes():
    stmt1 = Complex([Agent('x'), Agent('y'), Agent('z')])
    stmt2 = Complex([Agent('x'), Agent('y')])
    stmt3 = Phosphorylation(None, Agent('x'))

    stmts = ac.filter_complexes_by_size([stmt1, stmt2, stmt3])
    assert len(stmts) == 3
    stmts = ac.filter_complexes_by_size([stmt1, stmt2, stmt3],
                                        members_allowed=2)
    assert len(stmts) == 2


def test_map_db_refs():
    a = Agent('a', db_refs={'db1': 'a1', 'db2': 'a2'})
    b = Agent('b', db_refs={'db1': 'b1', 'db2': 'b2'})
    stmt = Activation(a, b)
    assert stmt.subj.db_refs['db1'] == 'a1'
    assert stmt.subj.db_refs['db2'] == 'a2'
    assert stmt.obj.db_refs['db1'] == 'b1'
    assert stmt.obj.db_refs['db2'] == 'b2'
    # Only provided IDs change, keep the rest unchanged
    db_refs_map = {('db1', 'a1'): 'A1',
                   ('db2', 'b2'): 'B2'}
    regr_stmt = ac.map_db_refs([stmt], db_refs_map=db_refs_map)[0]
    assert regr_stmt.subj.db_refs['db1'] == 'A1'
    assert regr_stmt.subj.db_refs['db2'] == 'a2'
    assert regr_stmt.obj.db_refs['db1'] == 'b1'
    assert regr_stmt.obj.db_refs['db2'] == 'B2'


def test_strip_supports():
    stmts = [deepcopy(st14), deepcopy(st15)]
    assert stmts[0].supports
    assert stmts[1].supported_by
    no_support = ac.strip_supports(stmts)
    assert not no_support[0].supports
    assert not no_support[0].supported_by
    assert not no_support[1].supports
    assert not no_support[1].supported_by


def test_normalize_active_forms():
    af1 = ActiveForm(Agent('a',
                     mods=[ModCondition('phosphorylation', 'T', 93),
                           ModCondition('phosphorylation', 'T', 63)]),
                     'activity', True)
    af2 = ActiveForm(Agent('a',
                     mods=[ModCondition('phosphorylation', 'T', 63),
                           ModCondition('phosphorylation', 'T', 93)]),
                     'activity', True)
    af3 = ActiveForm(Agent('a',
                     mods=[ModCondition('phosphorylation')]),
                     'activity', True)
    ph = Phosphorylation(Agent('a'), Agent('b'))
    act = Activation(Agent('b'), Agent('a'))
    stmts = [af1, af2, af3, ph, act]
    norm_stmts = ac.normalize_active_forms(stmts)
    assert len(norm_stmts) == 3
    norm_stmt_hashes = [stmt.get_hash() for stmt in norm_stmts]
    assert af1.get_hash() in norm_stmt_hashes
    assert af3.get_hash() not in norm_stmt_hashes
    assert ph.get_hash() in norm_stmt_hashes
    assert act.get_hash() in norm_stmt_hashes


def test_run_mechlinker():
    # Reduce activities
    a1 = Agent('a', location='cytoplasm')
    a2 = Agent('a', location='nucleus')
    af1 = ActiveForm(a1, 'activity', True)
    af2 = ActiveForm(a2, 'kinase', True)
    af3 = ActiveForm(a1, 'catalytic',True)
    stmts = [af1, af2, af3]
    stmts_out = ac.run_mechlinker(stmts, reduce_activities=True)
    for st in stmts_out:
        assert st.activity == 'kinase'
    # Reduce modifications
    phos1 = Phosphorylation(Agent('b'), Agent('a'))
    phos2 = Phosphorylation(Agent('c'), Agent('a'), 'T')
    phos3 = Phosphorylation(Agent('d'), Agent('a'), 'T', '143')
    stmts = [phos1, phos2, phos3]
    stmts_out = ac.run_mechlinker(stmts, reduce_modifications=True)
    assert len(stmts_out) == 3
    for st in stmts_out:
        assert st.residue == 'T'
        assert st.position == '143'
    # Replace activations
    af = ActiveForm(Agent('a', mods=[ModCondition('phosphorylation')]),
                    'activity', True)
    phos = Phosphorylation(Agent('b'), Agent('a'))
    act = Activation(Agent('b'), Agent('a'))
    stmts = [af, phos, act]
    stmts_out = ac.run_mechlinker(stmts, replace_activations=True)
    assert len(stmts_out) == 2
    # Require active forms
    af = ActiveForm(Agent('a', mods=[ModCondition('phosphorylation')]),
                    'activity', True)
    ph = Phosphorylation(Agent('a'), Agent('b'))
    stmts = [af, ph]
    stmts_out = ac.run_mechlinker(stmts, require_active_forms=True)
    assert len(stmts_out) == 2
    assert stmts_out[1].enz.mods, stmts_out


def test_filter_inconsequential():
    mc = ModCondition('phosphorylation', None, None, True)
    phos1 = Phosphorylation(None, Agent('a'))
    phos2 = Phosphorylation(Agent('a', mods=[mc]), Agent('b'))
    act1 = Activation(Agent('a', activity=ActivityCondition('kinase', True)),
                      Agent('b'), 'activity')
    act2 = Activation(Agent('c'), Agent('a'), 'kinase')
    stmts = [phos1, phos2, act1, act2]
    stmts_out = ac.filter_inconsequential(stmts)
    assert len(stmts_out) == 0, stmts_out
    mod_whitelist = {'b': [('phosphorylation', 'S', '315')]}
    act_whitelist = {'a': ['kinase']}
    stmts_out = ac.filter_inconsequential(
        stmts, acts=False, mod_whitelist=mod_whitelist)
    assert len(stmts_out) == 3, stmts_out
    stmts_out = ac.filter_inconsequential(stmts, mod_whitelist=mod_whitelist)
    assert len(stmts_out) == 1, stmts_out
    stmts_out = ac.filter_inconsequential(
        stmts, mods=False, act_whitelist=act_whitelist)
    assert len(stmts_out) == 3, stmts_out
    stmts_out = ac.filter_inconsequential(stmts, act_whitelist=act_whitelist)
    assert len(stmts_out) == 1, stmts_out
    stmts_out = ac.filter_inconsequential(
        stmts, mod_whitelist=mod_whitelist, act_whitelist=act_whitelist)
    assert len(stmts_out) == 2, stmts_out
