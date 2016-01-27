"""runit --- a module that integrates the other code into an
experimental run with data collection.
"""

import os
import random
import pprint as pp
import numpy as np
import multiprocess as mp
from mpi4py import MPI
from functools import partial
import pickle
import pdb
# import pandas as pd
# from pathos.multiprocessing import ProcessingPool as Pool
# import sqlite3
# import timeout

import part
import initiate
import develop
nimport blueprint
import export
import simulate
import selection

# DataFromRun = namedtuple('DataFromRun', ['fitness', 'original_genome',
#                                          'built_genome'])


def make_data_file(cond,
                   pop,
                   data_dir='../data/',
                   io_dir='../io/'):
    """
    Makes all the required folders to store the data and communications
    """
    # Data file
    cond = [i*10000 for i in cond]
    cond_str = 'r_00_{:02.0f}_b_00_{:02.0f}/'.format(*cond)
    pop_str = 'pop_{}.csv'.format(pop)
    the_dir = ''.join((data_dir, cond_str))
    if not os.path.isdir(the_dir):
        os.makedirs(the_dir)
    data_file = ''.join((the_dir, pop_str))
    # if exists make a copy
    while (os.path.isfile(data_file)):
        if data_file[-4] != ')':
            data_file = ''.join((data_file[:-4], '_(2).csv'))
        else:
            start_index = data_file.find('(') + 1
            stop_index = data_file.find(')')
            replace_char = str(int(data_file[start_index:stop_index]) + 1)
            data_file = ''.join((data_file[:start_index],
                                 replace_char,
                                 ').csv'))
    # IO file
    io_file = ''.join((io_dir, cond_str, 'pop_{}/'.format(pop)))
    if not os.path.isdir(io_file):
        os.makedirs(io_file)
    return [data_file, io_file]


def make_sql_table(dat_dir='./data/', data_file='population_0.db'):
    # import pdb
    # pdb.set_trace()
    # t = (i,)
    the_file = dat_dir + data_file
    count = 0
    while (os.path.isfile(the_file)):
        index = the_file.find('.db')
        if (count <= 10):
            the_file = the_file[:index-1] + str(count) + the_file[index:]
        elif (count > 10 and count <= 100):
            the_file = the_file[:index-2] + str(count) + the_file[index:]
        elif (count > 100 and count <= 1000):
            the_file = the_file[:index-3] + str(count) + the_file[index:]
        count += 1
    conn = sqlite3.connect(the_file)
    c = conn.cursor()
    # s = '''CREATE TABLE pop''' + str(i)
    # s += ''' (id INT PRIMARY KEY, generation INT, parent INT, '''
    # s += '''fitness REAL, reproduction_error_rate REAL, '''
    # s += '''buidling_error_rate REAL, germline_genes TEXT, '''
    # s += '''somaline_genes TEXT)'''
    # c.execute(s)
    c.execute('''CREATE TABLE pop (id INT PRIMARY KEY,
    generation INT, parent INT, fitness REAL,
    reproduction_error_rate REAL, buidling_error_rate REAL,
    germline_genes TEXT, somaline_genes TEXT)''')
    conn.commit()
    conn.close()
    return the_file


def abort_run(genome, genome_to_build):
    failed_run = [0, genome, genome_to_build]
    return failed_run


def run_one(genome, build_er, io_file, sim_num):
    proto_parts, genome_to_build = initiate.setup_agent(genome, build_er)
    parts_developed = develop.update_cycles(proto_parts)
    frame_selection = develop.select_frame_parts(parts_developed)
    if any([i == [] for i in frame_selection]):
        return abort_run(genome, genome_to_build)
    ann_selection = develop.select_ann_parts(parts_developed, frame_selection)
    if any([i == [] for i in ann_selection]):
        return abort_run(genome, genome_to_build)
    blueprints = blueprint.all_parts_to_send(parts_developed, frame_selection,
                                             ann_selection)
    export.export_all(blueprints[0], blueprints[1], blueprints[2],
                      blueprints[3], blueprints[4], blueprints[5],
                      blueprints[6], sim_num, io_file)
    return [simulate.run_simulation(io_file, sim_num), genome, genome_to_build]


def run_one_wrapper(sim_num, genomes, setup_data, io_file):
    run_data = run_one(genomes[sim_num], setup_data[2],
                       io_file, sim_num)
    data_row = [sim_num] + setup_data + [run_data[0], run_data[1][:9000],
                                         run_data[1][9000:],
                                         run_data[2][:9000],
                                         run_data[2][9000:]]
    return data_row


def run_generations(reproduction_error_rate, build_error_rate,
                    run_genomes, pop_num, generations=100):
    data_file, io_file = make_data_file(cond=[reproduction_error_rate,
                                              build_error_rate],
                                        pop=pop_num)
    col_names = ['agent', 'generation', 'reproduction_error_rate',
                 'build_error_rate', 'fitness', 'original_genome_1',
                 'original_genome_2', 'built_genome_1', 'built_genome_2']
    with open(data_file, 'w') as df:
        df.write('{},{},{},{},{},{},{},{},{}\n'.format(*col_names))
    for generation in xrange(generations):
        setup_data = [generation, reproduction_error_rate, build_error_rate]
        wrap_run_one_wrapper = partial(run_one_wrapper,
                                       genomes=run_genomes,
                                       io_file=io_file,
                                       setup_data=setup_data)
        sim_pool = mp.Pool(mp.cpu_count()-1)
        data_list = sim_pool.map(wrap_run_one_wrapper, xrange(60))
        data_list = map(wrap_run_one_wrapper, xrange(60))
        sim_pool.close()
        sim_pool.join()
        sort_data_list = sorted(data_list)
        fit_data = [i[4] for i in data_list]
        selection_genomes = [''.join((i[5], i[6])) for i in data_list]
        with open(data_file, 'a') as df:
            for row in data_list:
                df.write('{},{},{},{},{},{},{},{},{}\n'.format(*row))
        run_genomes = selection.next_generation(selection_genomes,
                                                fit_data,
                                                reproduction_error_rate)
        del(data_list)
        del(selection_genomes)
        del(fit_data)
        print "Done with generation ", generation

"""
# Script to run 1 population through all conditions, serially
if __name__ == '__main__':
    population = list()
    for a in xrange(60):
        population.append(initiate.generate_genome(18000))
    for rep_er_cond in xrange(5, 51, 5):
        rep_er = rep_er_cond / 10000.
        for build_er_cond in xrange(5, 51, 5):
            build_er = build_er_cond / 10000.
            random.seed(42)
            print "Start condition ", [rep_er, build_er]
            run_generations(rep_er, build_er, population, 0)
"""

"""
# Script to run 1 population under 100 conditions at the same time
CONDITIONS = list()
for i in range(5, 51, 5):
    r = i / 10000.
    for j in range(5, 51, 5):
        b = i / 10000.
        CONDITIONS.append([r, b])

population = [0] * 60

if __name__ = '__main__':
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    if rank == 0:
        for i in xrange(60):
            population[i] = initiate.generate_genome(18000)
    comm.Bcast(population, root=0)
    this_pop_run = 0
    rep_er, build_er = CONDITIONS[rank]
    random.seed(42)
    run_generations(rep_er, build_er, population, this_pop_run)
"""

"""
# Script to run X populations under each condition at the same time
if __name__ == '__main__':
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    population = list()
    for a in xrange(60):
        population.append(initiate.generate_genome(18000))
    for rep_er_cond in xrange(5, 51, 5):
        rep_er = rep_er_cond / 10000.
        for build_er_cond in xrange(5, 51, 5):
            build_er = build_er_cond / 10000.
            random.seed(42)
            run_generations(rep_er, build_er, population, rank)
"""


