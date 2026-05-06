import { Masthead } from './components/Masthead';
import { TimelineFeed } from './components/TimelineFeed';
import './styles.css';

export default function App() {
  return (
    <>
      <Masthead />
      <main className="body">
        <TimelineFeed />
      </main>
    </>
  );
}
