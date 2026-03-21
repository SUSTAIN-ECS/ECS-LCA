import lca_algebraic as agb

def stoch_impacts(ref_flow, impacts):
    problem, params, Y = agb.stats._stochastics(ref_flow[0], impacts)
    return Y