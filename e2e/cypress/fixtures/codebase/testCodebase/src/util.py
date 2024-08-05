#generated from chatgpt

# util.py
import numpy as np
import matplotlib.pyplot as plt

def logistic_growth(r, K, P0, t_max, dt):
    """
    Calculate the logistic growth of a population.

    Parameters:
    r (float): Growth rate
    K (int): Carrying capacity
    P0 (int): Initial population
    t_max (int): Time duration
    dt (float): Time step

    Returns:
    time (ndarray): Array of time points
    population (ndarray): Array of population values
    """
    time = np.arange(0, t_max, dt)
    population = np.zeros_like(time)
    population[0] = P0

    for t in range(1, len(time)):
        population[t] = population[t-1] + r * population[t-1] * (1 - population[t-1] / K) * dt
    
    return time, population

def plot_population_growth(time, population):
    """
    Plot the population growth over time.

    Parameters:
    time (ndarray): Array of time points
    population (ndarray): Array of population values
    """
    plt.figure(figsize=(10, 6))
    plt.plot(time, population, label='Population')
    plt.xlabel('Time')
    plt.ylabel('Population')
    plt.title('Logistic Growth Model')
    plt.legend()
    plt.grid(True)
    plt.show()


