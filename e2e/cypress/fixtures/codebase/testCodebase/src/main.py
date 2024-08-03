#generated from chatgpt

import numpy as np
import matplotlib.pyplot as plt

# Logistic growth model parameters
r = 0.1  # Growth rate
K = 1000  # Carrying capacity
P0 = 10  # Initial population
t_max = 100  # Time duration
dt = 1  # Time step

# Time array
time = np.arange(0, t_max, dt)

# Population array
population = np.zeros_like(time)
population[0] = P0

# Logistic growth model calculation
for t in range(1, len(time)):
    population[t] = population[t-1] + r * population[t-1] * (1 - population[t-1] / K) * dt

# Plot the results
plt.figure(figsize=(10, 6))
plt.plot(time, population, label='Population')
plt.xlabel('Time')
plt.ylabel('Population')
plt.title('Logistic Growth Model')
plt.legend()
plt.grid(True)
plt.show()

