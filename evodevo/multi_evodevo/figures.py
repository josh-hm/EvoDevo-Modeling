'''
Figure possibilities:
    Distribution of fitness effects X error_rates (X developmental_time_weighted_errors)
    Average fitness X error_rates
    Lineage fitness line-graphs
'''
from __future__ import print_function
import numpy as np
import pandas as pd
import seaborn as sb
import matplotlib.pyplot as plt


def find_parent(data, agent_num, agent_generation):
    '''
    Returns the data row of the parent for the given agent as pandas Series.
    '''
    if((not (1 <= agent_generation <= 99)) or
       (not (0 <= agent_num <= 59))):
        print ('Bad Input: ' + 'A: ' + str(agent_num) +
               'G: ' + str(agent_generation))
        raise IndexError
    parent_gen = data[data.generation == agent_generation]
    if agent_generation == 1:
        parent_gen = parent_gen.sort_values(by='fitness', ascending=False)
    if agent_num <= 11:
        parent_num = int(agent_num / 4)
    elif 12 <= agent_num <= 29:
        parent_num = int((agent_num - 13) / 3) + 3
    elif 30 <= agent_num <= 47:
        parent_num = int((agent_num - 31 / 2)) + 9
    elif 48 <= agent_num <= 59:
        parent_num = agent_num - 48 + 18
    return parent_gen.iloc[parent_num]


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in
            xrange(0, len(seq), size))


def hamming_distance(s1, s2, codon=False):
    '''
    Returns the hamming distance between the two strings
    '''
    if codon:
        s1c, s2c = [], []
        for part in chunker(s1, 3):
            s1c.append(part)
        for part in chunker(s2, 3):
            s2c.append(part)
        return sum(c1 != c2 for c1, c2 in itertools.izip(s1c, s2c))
    else:
        return sum(c1 != c2 for c1, c2 in itertools.izip(s1, s2))


def generation_grabber(data_frame, start, stop):
    return (data_frame[data_frame.generation == i]
            for i in range(start, stop))


def agent_grabber(generation_frame, start, stop):
    return (generation_frame.iloc[i]
            for i in range(start, stop))


def get_error_rates(data_file):
    data = pd.read_csv(data_file, engine='python', nrows=2)
    reproduction_error = int(round(data.reproduction_error_rate[0], 5) * 10000)
    build_error = int(round(data.build_error_rate[0], 5) * 10000)
    return [reproduction_error, build_error]


def graph_dfe_filler(data_file):
    data = pd.read_csv(data_file, engine='python')
    data['fitness'].fillna(0, inplace=True)
    limit = 500
    data.ix[data.fitness > limit, 'fitness'] = 0
    data.ix[data.fitness < -limit, 'fitness'] = 0
    histo_data = list()
    for gen_data in generation_grabber(data, 1, 100):
            for agent_data in agent_grabber(gen_data, 0, 60):
                agent_fit = agent_data.fitness
                parent_fit = find_parent(data, agent_data.agent,
                                         agent_data.generation).fitness
                histo_data.append(parent_fit - agent_fit)
    return histo_data


def graph_dist_fit_effect(data_file_list):
    histo_data = list()
    for f in data_file_list:
        histo_data += graph_dfe_filler(f)
    histo_data = pd.Series(histo_data)
    reproduction_error, build_error = get_error_rates(data_file_list[0])
    # c1 = pd.cut(histo_data, bins=4).value_counts(sort=False)
    # p1 = pd.cut(histo_data, bins=4).value_counts(sort=False,
    #                                              normalize=True)
    # print([c1, p1])
    plt.cla()
    sb.distplot(histo_data, kde=False)
    plt.xlabel('Fitness Effect')
    plt.ylabel('Frequency')
    plt.title('Distribution of Fitness Effects\nReproduction Error: {}; '
              'Build Error: {}'.format(reproduction_error, build_error))
    plt.xlim([-275, 275])
    plt.ylim([0, 3000])
    plt.plot()
    plt.savefig('../figs/dfe_figs/pop_1/RE_{}_BE_{}.png'.format(reproduction_error,
                                                                build_error))


def graph_avg_fits_filler(data_file):
    data = pd.read_csv(data_file, engine='python')
    data['fitness'].fillna(0, inplace=True)
    limit = 500
    data.ix[data.fitness > limit, 'fitness'] = 0
    data.ix[data.fitness < -limit, 'fitness'] = 0
    # reproduction_error = int(round(data.reproduction_error_rate[0], 2) * 100)
    build_error = int(round(data.build_error_rate[0], 2) * 100)
    avg_fit_data = list()
    for gen, gen_data in enumerate(generation_grabber(data, 0, 100)):
        pooler = 0
        gen_data = gen_data.sort_values(by='fitness', ascending=False)
        num = 30
        for agent_data in agent_grabber(gen_data, 0, num):
            pooler += agent_data.fitness
        avg = pooler / float(num)
        avg_fit_data.append([gen, avg])
    return avg_fit_data


def graph_avg_fits(data_file_list):
    avg_fit_data = list()
    for f in data_file_list:
        print (f, data_file_list)
        avg_fit_data += graph_avg_fits_filler(f)
    reproduction_error, build_error = get_error_rates(data_file_list[0])
    if len(data_file_list) > 1:
        assert ([reproduction_error, build_error] ==
                get_error_rates(data_file_list[1]))
    avg_x = np.array([i[0] for i in avg_fit_data])
    avg_y = np.array([i[1] for i in avg_fit_data])
    plt.cla()
    sb.regplot(x=avg_x, y=avg_y, fit_reg=True)
    plt.xlabel('Generations')
    plt.ylabel('Avg Fitness of Population')
    plt.title('Population Fitness Trend\nReproduction Error: {:02.0f}; '
              'Build Error: {:02.0f}'.format(reproduction_error, build_error))
    plt.xticks(range(0, 101, 10))
    plt.yticks(range(0, 121, 20))
    plt.xlim([0, 100])
    plt.ylim([0, 120])
    plt.plot()
    plt.savefig('../figs/m_avg_fit/pop_0/R_00_{:02.0f}_B_{:02.0f}.png'.format(reproduction_error,
                                                                              build_error))


def fix_data(ifn, ofn):
    data = pd.read_csv(ifn, engine='python')
    data['fitness'].fillna(0, inplace=True)
    data.ix[data.fitness > 500] = 0
    data = data.iloc[0:, 0:5]
    data.to_csv(ofn)

