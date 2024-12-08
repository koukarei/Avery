import { Step } from "../types/Step";
import { createContext, useState, useContext } from 'react';


type StepContextType = {
    activeStep: number;
    setActiveStep: React.Dispatch<React.SetStateAction<number>>;
    skipped: Set<number>;
    setSkipped: React.Dispatch<React.SetStateAction<Set<number>>>;
    triedTimes: number;
    setTriedTimes: React.Dispatch<React.SetStateAction<number>>;
  };
  

const initalStepProvider: StepContextType = {
    activeStep: 0,
    setActiveStep: ()=>{},
    skipped: new Set<number>(),
    setSkipped: ()=>{},
    triedTimes: 0,
    setTriedTimes: ()=>{}
}

export const StepContext = createContext(initalStepProvider);

export function StepProvider({ children }: { children: React.ReactNode }) {
  const [activeStep, setActiveStep] = useState<number>(0);
  const [skipped, setSkipped] =  useState<Set<number>>(new Set());
  const [triedTimes, setTriedTimes] = useState<number>(0);

  const contextValue = {
    activeStep, setActiveStep, skipped, setSkipped, triedTimes, setTriedTimes
}
    console.log(contextValue)

  return (<StepContext.Provider value={contextValue}>
    {children}
  </StepContext.Provider>)
}