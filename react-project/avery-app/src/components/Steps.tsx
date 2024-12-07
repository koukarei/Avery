import * as React from 'react';
import Box from '@mui/material/Box';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Container from '@mui/material/Container';

export const steps = [
  'Select leaderboards',
  'Describe the image',
  'Evaluation',
]

export default function HorizontalLinearStepper() {
  const [activeStep, setActiveStep] = React.useState(0);
  const [skipped, setSkipped] = React.useState(new Set<number>());
  const [triedTimes, setTriedTimes] = React.useState(0);

  const isStepOptional = (step: number) => {
    //return step === 1;
    return false;
  };

  const EnableRetried = (triedTimes: number) => {
    if (triedTimes <3){
      return true;
    }else{
      return false;
    }
  }

  const MessageToUser = (step: number) => {
    return(
      <Typography sx={{ mt: 2, mb: 1 }}>
        {step === 2 && EnableRetried(triedTimes)? 'Do you want to describe the image again?':step === 3 ? 'Checkout other leaderboards!':''}
      </Typography>
    )
  }

  const isStepSkipped = (step: number) => {
    return skipped.has(step);
  };

  const handleNext = () => {
    let newSkipped = skipped;
    if (isStepSkipped(activeStep)) {
      newSkipped = new Set(newSkipped.values());
      newSkipped.delete(activeStep);
    }

    setActiveStep((prevActiveStep) => prevActiveStep + 1);
    setSkipped(newSkipped);
    if (activeStep === 3){
      setTriedTimes((prevTriedTimes)=> prevTriedTimes + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleSkip = () => {
    if (!isStepOptional(activeStep)) {
      // You probably want to guard against something like this,
      // it should never occur unless someone's actively trying to break something.
      throw new Error("You can't skip a step that isn't optional.");
    }

    setActiveStep((prevActiveStep) => prevActiveStep + 1);
    setSkipped((prevSkipped) => {
      const newSkipped = new Set(prevSkipped.values());
      newSkipped.add(activeStep);
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
        ) : (
          <React.Fragment>
            
            <Box sx={{ display: 'flex', flexDirection: 'row', pt: 5 }}>
              <Button
                disabled={activeStep === 0}
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
                {activeStep === steps.length - 1 ? 'No' : 'Next'}
              </Button>
            </Box>
          </React.Fragment>
        
      )}
      </Container>
    </Box>
    
  );
}