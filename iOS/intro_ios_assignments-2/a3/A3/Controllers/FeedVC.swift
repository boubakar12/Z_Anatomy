//
//  FeedVC.swift
//  A3
//
//  Created by Vin Bui on 10/31/23.
//

import UIKit
import Alamofire

class FeedVC: UIViewController {
    
    // MARK: - Properties (view)
    private var collectionView: UICollectionView!
    private let refreshControl = UIRefreshControl()
    
    // MARK: - Properties (data)
    private var posts: [Post] = []
    
    // MARK: - viewDidLoad
    override func viewDidLoad() {
        super.viewDidLoad()
        
        title = "ChatDev"
        navigationController?.navigationBar.prefersLargeTitles = true
        view.backgroundColor = UIColor.a3.offWhite
        
        setupCollectionView()
        fetchPosts()
        
        refreshControl.addTarget(self, action: #selector(fetchPosts), for: .valueChanged)
        collectionView.refreshControl = refreshControl
    }
    
    // MARK: - Set Up Views
    private func setupCollectionView() {
        let layout = UICollectionViewFlowLayout()
        layout.sectionInset = UIEdgeInsets(top: 24, left: 16, bottom: 24, right: 16)
        layout.minimumLineSpacing = 16
        
        collectionView = UICollectionView(frame: view.bounds, collectionViewLayout: layout)
        collectionView.backgroundColor = UIColor.a3.offWhite
        collectionView.dataSource = self
        collectionView.delegate = self
        collectionView.register(PostUICollectionViewCell.self, forCellWithReuseIdentifier: "PostCell")
        collectionView.register(CreatePostCollectionViewCell.self, forCellWithReuseIdentifier: "CreatePostCell")
        
        view.addSubview(collectionView)
    }
    
    // MARK: - Fetch Posts
    @objc private func fetchPosts() {
        NetworkManager.shared.fetchPosts { [weak self] posts in
            guard let self = self else { return }
            self.posts = posts ?? []
            self.collectionView.reloadData()
            self.refreshControl.endRefreshing()
        }
    }
    
    // MARK: - Create Post
    private func createPost(message: String) {
        NetworkManager.shared.createPost(message: message) { [weak self] success in
            if success {
                self?.fetchPosts()
            } else {
                print("Failed to create post")
            }
        }
    }
    
    // MARK: - Post Button Action
    @objc private func postButtonTapped() {
        let alertController = UIAlertController(title: "New Post", message: "Enter your message", preferredStyle: .alert)
        alertController.addTextField { textField in
            textField.placeholder = "What's on your mind?"
        }
        let postAction = UIAlertAction(title: "Post", style: .default) { [weak self] _ in
            if let message = alertController.textFields?.first?.text, !message.isEmpty {
                self?.createPost(message: message)
            }
        }
        let cancelAction = UIAlertAction(title: "Cancel", style: .cancel, handler: nil)
        
        alertController.addAction(postAction)
        alertController.addAction(cancelAction)
        
        present(alertController, animated: true, completion: nil)
    }
}

// MARK: - UICollectionViewDelegate
extension FeedVC: UICollectionViewDelegate { }

// MARK: - UICollectionViewDataSource
extension FeedVC: UICollectionViewDataSource {

    func numberOfSections(in collectionView: UICollectionView) -> Int {
        return 2
    }

    func collectionView(_ collectionView: UICollectionView, numberOfItemsInSection section: Int) -> Int {
        return section == 0 ? 1 : posts.count
    }

    func collectionView(_ collectionView: UICollectionView, cellForItemAt indexPath: IndexPath) -> UICollectionViewCell {
        if indexPath.section == 0 {
            let cell = collectionView.dequeueReusableCell(withReuseIdentifier: "CreatePostCell", for: indexPath) as! CreatePostCollectionViewCell
            return cell
        } else {
            let cell = collectionView.dequeueReusableCell(withReuseIdentifier: "PostCell", for: indexPath) as! PostUICollectionViewCell
            let post = posts[indexPath.item]
            cell.configure(with: post)
            return cell
        }
    }

    func collectionView(_ collectionView: UICollectionView, layout collectionViewLayout: UICollectionViewLayout, insetForSectionAt section: Int) -> UIEdgeInsets {
        return UIEdgeInsets(top: 24, left: 16, bottom: 24, right: 16)
    }
}

// MARK: - UICollectionViewDelegateFlowLayout
extension FeedVC: UICollectionViewDelegateFlowLayout {

    func collectionView(_ collectionView: UICollectionView, layout collectionViewLayout: UICollectionViewLayout, sizeForItemAt indexPath: IndexPath) -> CGSize {
        let width = collectionView.frame.width - 32
        switch indexPath.section {
        case 0:
            return CGSize(width: width, height: 120)
        case 1:
            return CGSize(width: width, height: 80)
        default:
            return CGSize(width: width, height: 80)
        }
    }
}
