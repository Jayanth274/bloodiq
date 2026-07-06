const fetch = require('node-fetch');

async function run() {
  try {
    const resHyd = await fetch('http://localhost:3001/api/donors?blood_type=A%2B&city=Hyderabad');
    console.log('Hyd Status:', resHyd.status);
    console.log('Hyd Response:', await resHyd.json());

    const resSec = await fetch('http://localhost:3001/api/donors?blood_type=A%2B&city=Secunderabad');
    console.log('Sec Status:', resSec.status);
    console.log('Sec Response:', await resSec.json());
  } catch (e) {
    console.error(e);
  }
}
run();
