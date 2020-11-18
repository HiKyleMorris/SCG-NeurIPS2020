from scipy.sparse.linalg import eigsh
from utility import *
import time

DATASET_LIST = ['wow8', 'bitcoin', 'wikivot', 'referendum', 'slashdot', 'wikicon', 'epinions','wikipol']
ROUNDING_LIST = ['min_angle', 'randomized', 'max_obj', 'bansal']

def SCG(dataset, K, rounding_strategy, N=None, A=None):
    """ find K polarized communities """
    if dataset != 'sbm': # real-world dataset
        print('------ Running {}.txt ------'.format(dataset))
        # read graph
        N, A = read_graph("datasets/{}.txt".format(dataset))
    else: # synthetic modified SBM
        pass
    # eigendecompose the core KI-1 matrix
    D,U = EigenDecompose_Core(K)
    U = U[:, D.argsort()]
    D = np.sort(D)
    # initialization
    Y = np.zeros((N,K)) # to be determined, it must satisfy (1) Y_{i,1}=1/sqrt(K) if not neutral; 0 otherwise (2) Y_{i,2:} in {0, U_{1,2:}, ..., U_{K,2:}}
    C = np.array([-1 for i in range(N)]) # cluster assignment, C_i in {-1, 1, ..., K}, where -1 represent neutral
    mask = np.ones((N)) # list of nodes to be assigned
    maskA = A.copy() # adjacency matrix of the remaining graph

    for z in reversed(range(1,K)): # assign from the 1st, ..., the (K-1)-th, the K-th clusters
        lD, lU = eigsh(maskA, k=1, which='LA') # the eigenvector of the largest eigenvalue
        sD, _ = eigsh(maskA, k=1, which='SA') # the eigenvector of the smallest eigenvalue
        lD, sD = lD[0], sD[0]
        v = lU[:,0].reshape((-1))
        zi = K-z # this iteration decides the zi-th cluster
        # Round v to {-1,0,z}^n
        if rounding_strategy=='min_angle':
            v_round = round_by_min_angle(v, z, -1, mask, N)
        elif rounding_strategy=='randomized':
            v_round = round_by_randomized_vector(v, z, -1, mask, maskA, N)
        elif rounding_strategy=='max_obj':
            v_round = round_by_max_obj_one_threshold(v, z, -1, mask, maskA, N)
        elif rounding_strategy=='bansal':
            v_round = round_by_cc_bansal(z, -1, mask, maskA, N)
        # assign to the new cluster(s)
        for i in range(N):
            if v_round[i]==0: continue
            if z>1:
                if v_round[i]>0: C[i], Y[i,:] = zi, U[zi-1,:].copy() # assign to the zi-th cluster
            else:
                if v_round[i]>0: C[i], Y[i,:] = zi, U[zi-1,:].copy() # assign to the (K-1)-th cluster
                else: C[i], Y[i,:] = zi+1, U[zi,:].copy() # assign to the K-th cluster
        # check current objective value
        print('{}-th iteration obj={:.1f}, x^TAx/x^Tx={:.1f} in ({:.1f}, {:.1f})'.format(
            zi, compute_Obj(Y, A, K), compute_RayleighsQuotient(v_round, maskA), sD, lD))
        # set the assigned nodes to be skipped in the next iteration
        for i in range(N):
            if v_round[i]>0:
                # remove all edges incident to the assigned nodes
                maskA[i,:] = maskA[i,:].multiply(0)
                maskA[:,i] = maskA[:,i].multiply(0)
                mask[i] = 0 # remove the assigned node from the remaining list
    return C, Y, A, N, K

opt = parse_arg()
if opt.K == None: raise Exception('Error: please specify K')
try: K = int(opt.K)
except ValueError: raise Exception('Error: please specify K in integer')

if opt.dataset == 'all': # experiment: real-world datasets
    for dataset in DATASET_LIST:
        st = time.time()
        C, Y, A, N, K = SCG(dataset, K, opt.rounding_strategy)
        ed = time.time()
        check_result_KCG(C, Y, A, N, K, ed-st)
elif opt.dataset in DATASET_LIST:
    st = time.time()
    C, Y, A, N, K = SCG(opt.dataset, K, opt.rounding_strategy)
    ed = time.time()
    check_result_KCG(C, Y, A, N, K, ed-st)
elif opt.dataset == 'sbm' and K>0: # experiment: synthetic network generated by m-SSBM
    try: N = int(opt.sbm_nv)
    except ValueError: raise Exception('Error: please specify the graph size in integer')
    try: nC = int(opt.sbm_nc)
    except ValueError: raise Exception('Error: please specify the community size in integer')
    for t in range(20):
        print('------------ [Round #{}] ------------'.format(t))
        for p in [0.1*(i) for i in range(7)]:
            print('------ Running SBM [p={:.1f}] ------'.format(p))
            _, A = gen_SBM(p, K, N, nC)
            st = time.time()
            C, Y, A, N, K = SCG('sbm', K, opt.rounding_strategy, N=N, A=A)
            ed = time.time()
            check_result_KCG(C, Y, A, N, K, ed-st)
            precision, recall, precs, recs, f1_score = compute_accuracy(C, nC, K)
            print('Accuracy: precision={:.2f}, recall={:.2f}, f1-score={:.2f}'.format(precision, recall, f1_score))
            print(precs)
            print(recs)
else:
    raise Exception('Error: please specify dataset name in {} or just leave it blank to run ALL'.format(DATASET_LIST))
