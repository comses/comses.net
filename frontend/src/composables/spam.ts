export function useFormTimer() {
  const loadedTime = new Date();

  const getSubmitTime = () => {
    return new Date();
  };

  return {
    loadedTime,
    getSubmitTime,
  };
}

export type TimerFields = {
  loadedTime: Date;
  submitTime: Date;
};
