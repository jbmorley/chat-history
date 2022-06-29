import { useEffect, useState } from 'react'
import InfiniteScroll from 'react-infinite-scroll-component'
import { range } from 'remeda'

function useWindowDimensions() {
	const [windowSize, setWindowSize] = useState<{
		width?: number
		height?: number
	}>({})

	useEffect(() => {
		function handleResize() {
			setWindowSize({ width: window.innerWidth, height: window.innerHeight })
		}
		window.addEventListener('resize', handleResize)

		handleResize()

		return () => window.removeEventListener('resize', handleResize)
	}, [])

	return windowSize
}

export function App() {
	const vpWidth = useWindowDimensions().width!
	const sidebarWidth = vpWidth / 6
	const chatWidth = vpWidth - sidebarWidth
	const [selectedChat, setSelectedChat] = useState(0)

	return (
		<div className="flex w-screen h-screen fixed">
			<div className="flex flex-col" style={{ width: sidebarWidth }}>
				<p className="text-4xl">Chats</p>
				<div className="flex flex-col overflow-y-auto">
					{range(0, 160).map((i) => (
						<p onClick={() => setSelectedChat(i)}>Chat with {i}</p>
					))}
				</div>
			</div>

			<div className="w-1 bg-red-500" />

			<div className="flex flex-col" style={{ width: chatWidth }}>
				<p className="text-4xl">Chat with {selectedChat}</p>
				<div className="flex flex-col-reverse overflow-y-auto">
					<InfiniteScroll
						inverse
						dataLength={30}
						next={() => {}}
						hasMore={false}
						loader={null}
					>
						{range(0, 90).map((i) => {
							const mine = i % 3
							return (
								<div>
									<div
										className={mine ? 'w-1/2' : 'w-1/2 flex-row-reverse flex'}
									>
										<p>Message {i}</p>
									</div>
								</div>
							)
						})}
					</InfiniteScroll>
				</div>
			</div>
		</div>
	)
}
