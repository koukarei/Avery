export const steps = [
    'Select leaderboards',
    'Describe the image',
    'Evaluation',
  ]

export type Step={
    activeStep?: number;
    skipped?: Set<number>;
    triedTimes?: number;
    optionalStep?: boolean;
}
