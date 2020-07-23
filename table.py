# Python code to find frequency of each word 
def freq(str): 
  
    # break the string into list of words  
    str2 = [] 
  
    # loop till string values present in list str 
    for i in str:              
  
        # checking for the duplicacy 
        if i not in str2: 
  
            # insert value in str2 
            str2.append(i)  
              
    values = []
    for i in range(0, len(str2)): 
  
        # count the frequency of each word(present  
        # in str2) in str and print 
        #print('Frequency of', str2[i], 'is :', str.count(str2[i]))

        if str.count(str2[i]) > 1:
            #x = (str2[i], str.count(str2[i]))
            values.append(str2[i])
    return values
  
def main(): 
    str ='apple mango apple orange orange apple guava mango mango'
    freq(str)                     
  
if __name__=="__main__": 
    main()             # call main function 