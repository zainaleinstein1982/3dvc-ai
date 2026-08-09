import dynamic from 'next/dynamic';
const Room = dynamic(() => import('@/components/Room'), { ssr: false });
export default function Page() { return <Room />; }
