import * as React from 'react';
import Box from '@mui/material/Box';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Container from '@mui/material/Container';
import { Theme } from '@mui/material/styles';
import {steps} from '../types/Step';
import { StepContext } from '../providers/StepProvider';

interface stepProps {
  theme: Theme;
}

export default function HorizontalLinearStepper({theme}: stepProps) {
  const {
    activeStep,
    setActiveStep,
    skipped,
    setSkipped,
    triedTimes,
    setTriedTimes
  } = React.useContext(StepContext);

  const isStepOptional = (step: number) => {
    //return step === 1;
    return false;
  };

  const EnableRetried = (triedTimes: number) => {
    return triedTimes < 3;
  }

  const MessageToUser = (step: number) => {
    return(
      <Typography variant='h3' sx={{ mt: 2, mb: 1, color: theme.palette.text.primary}}>
        {step === 2 && EnableRetried(triedTimes)? 'Do you want to describe the image again?':step === 3 ? 'Checkout other leaderboards!':''}
      </Typography>
    )
  }

  const isStepSkipped = (step: number) => {
    return skipped?.has(step)|| false;
  };

  const handleNext = () => {
    let newSkipped = skipped;
    if (activeStep !== undefined && isStepSkipped(activeStep)) {
      newSkipped = new Set(newSkipped?.values() || []);
      if (activeStep !== undefined) {
        newSkipped.delete(activeStep);
      }
    }

    setActiveStep((prevActiveStep) => prevActiveStep + 1);
    setSkipped(newSkipped);
    if (activeStep === 1){
      setTriedTimes((prevTriedTimes)=> prevTriedTimes + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleSkip = () => {
    if (activeStep !== undefined && !isStepOptional(activeStep)) {

      // You probably want to guard against something like this,
      // it should never occur unless someone's actively trying to break something.
      throw new Error("You can't skip a step that isn't optional.");
    }

    setActiveStep((prevActiveStep) => prevActiveStep + 1);
    setSkipped((prevSkipped: Set<number>) => {
      const newSkipped = new Set(prevSkipped.values());
      newSkipped.add(activeStep!);
      return newSkipped;
    });
    
  };

  const handleReset = () => {
    setActiveStep(0);
    setTriedTimes(0);
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Container sx={{position:'absolute',top:'7px', left:'0' ,width: '70vw'}}>
        <Stepper activeStep={activeStep}>
          {steps.map((label, index) => {
            const stepProps: { completed?: boolean } = {};
            const labelProps: {
              optional?: React.ReactNode;
            } = {};
            if (isStepOptional(index)) {
              labelProps.optional = (
                <Typography variant="caption">Optional</Typography>
              );
            }
            if (isStepSkipped(index)) {
              stepProps.completed = false;
            }
            return (
              <Step key={label} {...stepProps}>
                <StepLabel {...labelProps}>{label}</StepLabel>
              </Step>
            );
          })}
        </Stepper>
      </Container>
      <Container sx={{position:'absolute',top:'0', right:'0' ,width: '30vw'}}>
        {MessageToUser(activeStep)}
      </Container>
      <Container sx={{position:'absolute',bottom:'7px', right:'0' ,width: '50vw'}}>
        {activeStep === steps.length ? (
          <React.Fragment>
            <Box sx={{ display: 'flex', flexDirection: 'row', pt: 2 }}>
              <Box sx={{ flex: '1 1 auto' }} />
              <Button onClick={handleReset}>Go</Button>
            </Box>
          </React.Fragment>
        ) : 
        (
          <React.Fragment>
            <Box sx={{ display: 'flex', flexDirection: 'row', pt: 5 }}>
              <Button
                disabled={activeStep === 0 || !EnableRetried(triedTimes)}
                onClick={handleBack}
                sx={{ mr: 1 }}
              >
                {activeStep === steps.length - 1 ? 'Yes' : 'Back'}
              </Button>
              <Box sx={{ flex: '1 1 auto' }} />
              {isStepOptional(activeStep) && (
                <Button onClick={handleSkip} sx={{ mr: 1 }}>
                  Skip
                </Button>
              )}
              <Button onClick={handleNext}>
                {activeStep === steps.length - 1 && EnableRetried(triedTimes) ? 'No' : 'Next'}
              </Button>
            </Box>
          </React.Fragment>
        
      )}
      </Container>
    </Box>
    
  );
}