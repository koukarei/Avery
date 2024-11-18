import robot from './avery_robot.png';
import './App.css';
import  HorizontalLinearStepper  from './components/Steps';

function App() {
  return (
    <div className="App">
      <div className='Stepper'><HorizontalLinearStepper /></div>
      
      <img src={robot} className="Robot" alt="robot" />
    </div>
  );
}

export default App;
