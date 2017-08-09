from datetime import datetime


def log_sort(file1, file2):
    #file1 and file2 should be strings with .txt extensions
    def sort_key(line):
        #print(line.split('|')[0])
        return datetime.strptime(line.split('|')[0],'%Y-%m-%d %H:%M:%S')
    comp_array = []

    with open(file1, "r") as f1:
        for i, l in enumerate(f1):
            pass
        f1_count = i + 1
    for i in range(f1_count+1):
        f1 = open(file1, "r")
        x = f1.readline()
        f1.close()
        comp_array.append(x)


    with open(file1, "r") as f2:
        for j, l in enumerate(f2):
            pass
        f2_count = i + 1

    for i in range(f2_count+1):
        f2 = open(file2, "r")
        x = f2.readline()
        f2.close()
        comp_array.append(x)


    out_array = sorted(comp_array,key = sort_key)

    with open("final_out.log", "w") as f3:
        for line in out_array:
            f3.write(line)

if __name__ == '__main__':
    file1 = "test.log"
    file2 = "test2.log"
    log_sort(file1, file2)
