import json

with open("sample.json", 'r') as file:
    x = json.load(file)

perc_agr = []
uniq_word = []
total_word = []
repition_coef = []

for key, val in x.items():
    if key == "AZ_Error_Log" or key == "Records_Processed":
        continue
    perc_agr.append(x[key]["Percent_Agreed"])
    uniq_word.append(x[key]["Unique_Word_Count"]),
    total_word.append(x[key]["Total_Word_Count"]),
    repition_coef.append(x[key]["Repition_Coeff"])

results = [[],[],[],[]]

results[0].append(sum(perc_agr)/len(perc_agr))
results[0].append(max(perc_agr))
results[0].append(min(perc_agr))

results[1].append(sum(uniq_word)/len(uniq_word))
results[1].append(max(uniq_word))
results[1].append(min(uniq_word))

results[2].append(sum(total_word)/len(total_word))
results[2].append(max(total_word))
results[2].append(min(total_word))

results[3].append(sum(repition_coef)/len(repition_coef))
results[3].append(max(repition_coef))
results[3].append(min(repition_coef))

for t in results:
    print(t)
